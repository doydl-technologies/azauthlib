// Copyright 2024 DOYDL Technologies. Licensed under the Apache License, Version 2.0.
// Native per-user MSI host. Closing an active installation requests cancellation,
// never termination of the Windows Installer transaction.
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <windowsx.h>
#include <msi.h>
#include <msiquery.h>
#include <shellapi.h>
#include <shlobj.h>
#include <gdiplus.h>
#include <bcrypt.h>
#include <atomic>
#include <thread>
#include <string>
#include <vector>
#include <filesystem>
#include <fstream>
#include <algorithm>
#include "windows_progress.h"

using namespace Gdiplus;
namespace {
constexpr int width = 640, height = 454;
constexpr UINT beginMessage = WM_APP + 1, finishMessage = WM_APP + 2;
enum Phase { preparing, installing, stopping, complete, cancelled, failed };
std::atomic<Phase> phase{preparing};
std::atomic<bool> cancelRequested{false}, cancelSent{false};
std::atomic<int> progressFraction{-1};
std::atomic<bool> rollingBack{false};
InstallerProgress progress;
HWND window = nullptr;
UINT resultCode = 0;
std::thread worker;
Bitmap* brand = nullptr;
IStream* brandStream = nullptr;
Bitmap* mascot = nullptr;
IStream* mascotStream = nullptr;
int tick = 0;
bool cancelDuringCopy = false, injectFailure = false;
bool previewWindow = false;
std::wstring action;

void text(Graphics& g, const wchar_t* value, float x, float y, float w, float h,
          float size, Color color, bool bold = false, bool centered = false) {
  FontFamily family(L"Segoe UI");
  Font font(&family, size, bold ? FontStyleBold : FontStyleRegular, UnitPixel);
  SolidBrush brush(color);
  StringFormat format;
  format.SetTrimming(StringTrimmingEllipsisCharacter);
  if(centered) format.SetAlignment(StringAlignmentCenter);
  g.DrawString(value, -1, &font, RectF(x, y, w, h), &format, &brush);
}
void paint(Graphics& g) {
  g.SetSmoothingMode(SmoothingModeAntiAlias);
  g.SetTextRenderingHint(TextRenderingHintAntiAliasGridFit);
  g.SetInterpolationMode(InterpolationModeHighQualityBicubic);
  g.Clear(Color(255,255,255,255));
  if (brand && brand->GetLastStatus() == Ok)
    g.DrawImage(brand, RectF(20,14,184,184.0f*brand->GetHeight()/brand->GetWidth()));
  else text(g,L"azauthlib",20,20,200,45,28,Color(255,12,28,43),true);
  Pen controls(Color(255,16,28,36),1.8f);
  g.DrawLine(&controls,565.0f,31.0f,579.0f,31.0f);
  g.DrawLine(&controls,606.0f,25.0f,618.0f,37.0f);
  g.DrawLine(&controls,618.0f,25.0f,606.0f,37.0f);
  const Phase p = phase.load();
  const wchar_t* title = p == complete ? L"Installation complete" : p == cancelled ? L"Installation cancelled"
      : p == failed ? L"Setup couldn't finish" : L"Installing...";
  const wchar_t* description = p == complete ? L"Find azauthlib Desktop in your Start Menu."
      : p == cancelled ? L"Your saved profiles and credentials have been retained."
      : p == failed ? L"Close setup and try again after checking the error below."
      : p == stopping ? L"Please wait while Windows Installer restores changes."
      : L"Please wait while azauthlib Desktop is installed.";
  text(g,title,30,80,580,32,21,Color(255,17,28,36),false,true);
  text(g,description,30,122,580,30,11,Color(255,54,65,73),false,true);
  if(mascot && mascot->GetLastStatus()==Ok) {
    const float h=200.0f, w=h*mascot->GetWidth()/mascot->GetHeight();
    g.DrawImage(mascot,RectF((width-w)/2,153,w,h));
  }
  SolidBrush track(Color(255,203,209,212)), accent(Color(255,14,138,115));
  g.FillRectangle(&track,64,376,512,4);
  if(p==complete) g.FillRectangle(&accent,64,376,512,4);
  else if(p<complete) {
    int fraction=progressFraction.load();
    if(fraction>=0) g.FillRectangle(&accent,64,376,512*std::min(fraction,980)/1000,4);
    else {
      int pos=tick*6%622-110;
      int left=std::max(0,pos), right=std::min(512,pos+110);
      if(right>left) g.FillRectangle(&accent,64+left,376,right-left,4);
    }
  }
  std::wstring status = p == preparing ? L"Unpacking..."
      : p == stopping ? (rollingBack ? L"Rolling back changes" : L"Cancelling...")
      : p == installing ? L"Copying files"
      : p == complete ? (resultCode==ERROR_SUCCESS_REBOOT_REQUIRED ? L"Complete. Windows requests a restart." : L"Complete. Setup will close shortly.")
      : p == cancelled ? L"Aborted"
      : L"Windows Installer error " + std::to_wstring(resultCode);
  text(g,status.c_str(),32,394,576,34,12,Color(255,30,48,55),false,true);
}
void loadImage(int id, Bitmap*& image, IStream*& stream) {
  HRSRC resource = FindResourceW(nullptr, MAKEINTRESOURCEW(id), RT_RCDATA);
  if (!resource) return;
  DWORD size = SizeofResource(nullptr,resource);
  HGLOBAL memory = GlobalAlloc(GMEM_MOVEABLE,size);
  if (!memory) return;
  void* buffer = GlobalLock(memory);
  if (!buffer) { GlobalFree(memory); return; }
  memcpy(buffer,LockResource(LoadResource(nullptr,resource)),size);
  GlobalUnlock(memory);
  if (CreateStreamOnHGlobal(memory,TRUE,&stream) != S_OK) { GlobalFree(memory); return; }
  image = Bitmap::FromStream(stream);
}
bool preview(const std::wstring& path) {
  Bitmap bitmap(width,height,PixelFormat32bppARGB);
  { Graphics g(&bitmap); paint(g); }
  UINT count=0,size=0; GetImageEncodersSize(&count,&size);
  std::vector<BYTE> buffer(size);
  auto codecs = reinterpret_cast<ImageCodecInfo*>(buffer.data());
  GetImageEncoders(count,size,codecs);
  for(UINT i=0;i<count;++i) if(wcscmp(codecs[i].MimeType,L"image/png")==0)
    return bitmap.Save(path.c_str(),&codecs[i].Clsid,nullptr)==Ok;
  return false;
}
bool extract(const std::wstring& path) {
  HRSRC resource=FindResourceW(nullptr,MAKEINTRESOURCEW(101),RT_RCDATA);
  HRSRC expectedResource=FindResourceW(nullptr,MAKEINTRESOURCEW(103),RT_RCDATA);
  if(!resource || !expectedResource) return false;
  auto bytes=static_cast<const BYTE*>(LockResource(LoadResource(nullptr,resource)));
  auto expected=static_cast<const BYTE*>(LockResource(LoadResource(nullptr,expectedResource)));
  DWORD size=SizeofResource(nullptr,resource);
  if(!bytes || !expected || SizeofResource(nullptr,expectedResource)!=32) return false;
  HANDLE file=CreateFileW(path.c_str(),GENERIC_WRITE,0,nullptr,CREATE_NEW,FILE_ATTRIBUTE_TEMPORARY,nullptr);
  if(file==INVALID_HANDLE_VALUE) return false;
  BCRYPT_ALG_HANDLE algorithm=nullptr; BCRYPT_HASH_HANDLE hash=nullptr;
  bool okay=BCryptOpenAlgorithmProvider(&algorithm,BCRYPT_SHA256_ALGORITHM,nullptr,0)==0;
  if(okay) okay=BCryptCreateHash(algorithm,&hash,nullptr,0,nullptr,0,0)==0;
  for(DWORD offset=0;okay && offset<size;) {
    if(cancelRequested) { okay=false; break; }
    DWORD chunk=std::min<DWORD>(1024*1024,size-offset), written=0;
    okay=WriteFile(file,bytes+offset,chunk,&written,nullptr) && written==chunk
        && BCryptHashData(hash,const_cast<PUCHAR>(bytes+offset),chunk,0)==0;
    offset+=chunk;
  }
  BYTE digest[32]={};
  if(okay) okay=BCryptFinishHash(hash,digest,32,0)==0 && memcmp(digest,expected,32)==0;
  if(hash) BCryptDestroyHash(hash);
  if(algorithm) BCryptCloseAlgorithmProvider(algorithm,0);
  if(!CloseHandle(file)) okay=false;
  if(!okay) DeleteFileW(path.c_str());
  return okay;
}
std::wstring cachePackage(const std::wstring& extracted) {
  std::filesystem::path base;
#ifdef AZAUTHLIB_INSTALLER_TEST
  wchar_t testPath[32768]={};
  if(!GetEnvironmentVariableW(L"AZAUTHLIB_TEST_CACHE",testPath,32768)) return L"";
  base=testPath;
#else
  PWSTR local=nullptr;
  if(SHGetKnownFolderPath(FOLDERID_LocalAppData,0,nullptr,&local)!=S_OK) return L"";
  base=std::filesystem::path(local)/L"azauthlib"/L"installer-cache";
  CoTaskMemFree(local);
#endif
  HRSRC resource=FindResourceW(nullptr,MAKEINTRESOURCEW(103),RT_RCDATA);
  auto digest=static_cast<const BYTE*>(LockResource(LoadResource(nullptr,resource)));
  std::wstring key;
  for(int i=0;i<32;++i) { key+=L"0123456789abcdef"[digest[i]>>4]; key+=L"0123456789abcdef"[digest[i]&15]; }
  std::error_code error;
  auto directory=base/key;
  std::filesystem::create_directories(directory,error);
  if(error) return L"";
  auto target=directory/L"azauthlib.msi";
  const bool exists=std::filesystem::exists(target,error);
  if(error) return L"";
  if(!exists) {
    // Publish a complete source package atomically so interrupted copies cannot
    // leave a partial MSI at the path Windows Installer will use for repair.
    GUID id={};
    if(CoCreateGuid(&id)!=S_OK) return L"";
    wchar_t suffix[40]={}; StringFromGUID2(id,suffix,40);
    auto pending=directory/(std::wstring(suffix)+L".tmp");
    if(!CopyFileW(extracted.c_str(),pending.c_str(),TRUE)) return L"";
    bool moved=MoveFileExW(pending.c_str(),target.c_str(),MOVEFILE_WRITE_THROUGH);
    DWORD moveError=moved ? ERROR_SUCCESS : GetLastError();
    DeleteFileW(pending.c_str());
    if(!moved && moveError!=ERROR_ALREADY_EXISTS && moveError!=ERROR_FILE_EXISTS) return L"";
  }
  HRSRC payload=FindResourceW(nullptr,MAKEINTRESOURCEW(101),RT_RCDATA);
  const auto bytes=static_cast<const BYTE*>(LockResource(LoadResource(nullptr,payload)));
  DWORD length=SizeofResource(nullptr,payload);
  std::ifstream stream(target,std::ios::binary);
  if(!stream || std::filesystem::file_size(target,error)!=length || error) return L"";
  std::vector<char> block(1024*1024);
  for(DWORD offset=0;offset<length;) {
    DWORD count=std::min<DWORD>(static_cast<DWORD>(block.size()),length-offset);
    if(!stream.read(block.data(),count) || memcmp(block.data(),bytes+offset,count)) return L"";
    offset+=count;
  }
  return directory.wstring();
}
int CALLBACK callback(LPVOID, UINT message, MSIHANDLE record) {
  const UINT kind=message & 0xff000000;
  if(kind==INSTALLMESSAGE_PROGRESS) {
    progress.update(MsiRecordGetInteger(record,1),MsiRecordGetInteger(record,2),MsiRecordGetInteger(record,3));
    if(progress.initialized && progress.backwards) { rollingBack=true; phase=stopping; }
    progressFraction=progress.fraction();
  } else if(kind==INSTALLMESSAGE_ACTIONDATA) {
    progress.actionData();
    progressFraction=progress.fraction();
  }
  if(kind==INSTALLMESSAGE_ACTIONSTART) {
    wchar_t name[256]={}; DWORD size=256;
    MsiRecordGetStringW(record,1,name,&size); action=name;
#ifdef AZAUTHLIB_INSTALLER_TEST
    if(action==L"InjectedFailure") {
      wchar_t trace[32768]={}, destination[32768]={};
      GetEnvironmentVariableW(L"AZAUTHLIB_TEST_TRACE",trace,32768);
      GetEnvironmentVariableW(L"AZAUTHLIB_TEST_DEST",destination,32768);
      std::ifstream data(std::filesystem::path(destination)/L"app"/L"data.txt");
      std::string content; std::getline(data,content);
      std::ofstream marker(std::filesystem::path(trace),std::ios::app);
      marker<<"InjectedFailure after copy: "<<content<<"\n";
    }
#endif
  }
#ifdef AZAUTHLIB_INSTALLER_TEST
  if(cancelDuringCopy && kind==INSTALLMESSAGE_ACTIONDATA) {
    wchar_t file[1024]={}; DWORD count=1024;
    MsiRecordGetStringW(record,1,file,&count);
    if(wcsstr(file,L"chunk-")!=nullptr) cancelRequested=true;
  }
#endif
  if(cancelRequested && (kind==INSTALLMESSAGE_PROGRESS || kind==INSTALLMESSAGE_ACTIONDATA)
      && !cancelSent.exchange(true)) {
    phase=stopping;
    return IDCANCEL;
  }
  if(kind==INSTALLMESSAGE_FILESINUSE || kind==INSTALLMESSAGE_RMFILESINUSE) return IDCANCEL;
  return IDOK;
}
void install() {
  wchar_t base[MAX_PATH]={}, temporary[MAX_PATH]={};
  UINT result=ERROR_WRITE_FAULT;
  if(GetTempPathW(MAX_PATH,base) && GetTempFileNameW(base,L"AZI",0,temporary)) {
    DeleteFileW(temporary);
    if(CreateDirectoryW(temporary,nullptr)) {
      const std::wstring msi=std::wstring(temporary)+L"\\azauthlib.msi";
      if(extract(msi)) {
        if(cancelRequested) result=ERROR_INSTALL_USEREXIT;
        else {
          auto cache=cachePackage(msi);
          if(cache.empty()) { DeleteFileW(msi.c_str()); RemoveDirectoryW(temporary); PostMessageW(window,finishMessage,ERROR_WRITE_FAULT,0); return; }
          phase=installing;
#ifdef AZAUTHLIB_INSTALLER_TEST
          wchar_t logPath[32768]={};
          if(GetEnvironmentVariableW(L"AZAUTHLIB_TEST_LOG",logPath,32768))
            MsiEnableLogW(INSTALLLOGMODE_VERBOSE,logPath,INSTALLLOGATTRIBUTES_FLUSHEACHLINE);
#endif
          INSTALLUILEVEL old=MsiSetInternalUI(INSTALLUILEVEL_NONE,nullptr);
          INSTALLUI_HANDLER_RECORD previous=nullptr;
          UINT hooked=MsiSetExternalUIRecord(callback, INSTALLLOGMODE_PROGRESS | INSTALLLOGMODE_ACTIONDATA |
              INSTALLLOGMODE_ACTIONSTART | INSTALLLOGMODE_FILESINUSE | INSTALLLOGMODE_RMFILESINUSE,
              nullptr,&previous);
          if(hooked==ERROR_SUCCESS) {
            std::wstring properties=L"REBOOT=ReallySuppress SOURCELIST=\""+cache+L"\"";
#ifdef AZAUTHLIB_INSTALLER_TEST
            if(injectFailure) properties+=L" AZ_TEST_FAIL=1";
#endif
            result=MsiInstallProductW(msi.c_str(),properties.c_str());
#ifdef AZAUTHLIB_INSTALLER_TEST
            wchar_t trace[32768]={};
            if(GetEnvironmentVariableW(L"AZAUTHLIB_TEST_TRACE",trace,32768)) {
              std::ofstream marker(std::filesystem::path(trace),std::ios::app);
              marker<<"MSI progress initialized: "<<progress.initialized
                    <<"; rollback: "<<rollingBack.load()<<"\n";
            }
#endif
            MsiSetExternalUIRecord(previous,0,nullptr,nullptr);
          } else result=hooked;
          MsiSetInternalUI(old,nullptr);
        }
        DeleteFileW(msi.c_str());
      } else if(cancelRequested) result=ERROR_INSTALL_USEREXIT;
      RemoveDirectoryW(temporary);
    }
  }
  PostMessageW(window,finishMessage,result,0);
}
void closeRequest() {
  if(previewWindow) { DestroyWindow(window); return; }
  if(phase>=complete) { DestroyWindow(window); return; }
  if(cancelRequested) return;
  if(MessageBoxW(window,L"Do you want to cancel the installation? Setup will remain open while changes are rolled back.",
      L"Cancel installation?",MB_YESNO|MB_ICONQUESTION|MB_DEFBUTTON2)==IDYES) {
    if(phase>=complete) { DestroyWindow(window); return; }
    cancelRequested=true; phase=stopping;
  }
}
LRESULT CALLBACK windowProc(HWND hwnd,UINT message,WPARAM w,LPARAM l) {
  switch(message) {
    case WM_CREATE: window=hwnd; SetTimer(hwnd,1,25,nullptr); PostMessageW(hwnd,beginMessage,0,0); return 0;
    case beginMessage:
      if(previewWindow) { phase=installing; progressFraction=420; }
      else worker=std::thread(install);
      return 0;
    case finishMessage:
      resultCode=static_cast<UINT>(w);
      phase=resultCode==ERROR_SUCCESS || resultCode==ERROR_SUCCESS_REBOOT_REQUIRED ? complete
          : resultCode==ERROR_INSTALL_USEREXIT ? cancelled : failed;
      InvalidateRect(hwnd,nullptr,FALSE);
      if(phase==complete) SetTimer(hwnd,2,2500,nullptr);
#ifdef AZAUTHLIB_INSTALLER_TEST
      else SetTimer(hwnd,2,100,nullptr);
#endif
      return 0;
    case WM_TIMER: if(w==2) DestroyWindow(hwnd); else { ++tick; InvalidateRect(hwnd,nullptr,FALSE); } return 0;
    case WM_PAINT: {
      PAINTSTRUCT ps; HDC screen=BeginPaint(hwnd,&ps); RECT rect; GetClientRect(hwnd,&rect);
      HDC memory=CreateCompatibleDC(screen); HBITMAP bitmap=CreateCompatibleBitmap(screen,rect.right,rect.bottom);
      HGDIOBJ old=SelectObject(memory,bitmap);
      { Graphics g(memory); g.ScaleTransform(float(rect.right)/width,float(rect.bottom)/height); paint(g); }
      BitBlt(screen,0,0,rect.right,rect.bottom,memory,0,0,SRCCOPY);
      SelectObject(memory,old); DeleteObject(bitmap); DeleteDC(memory); EndPaint(hwnd,&ps); return 0;
    }
    case WM_CLOSE: closeRequest(); return 0;
    case WM_NCHITTEST: {
      POINT point={GET_X_LPARAM(l),GET_Y_LPARAM(l)}; ScreenToClient(hwnd,&point);
      RECT rect; GetClientRect(hwnd,&rect);
      const int x=point.x*width/std::max(1L,rect.right), y=point.y*height/std::max(1L,rect.bottom);
      return y>=0 && y<64 && x<548 ? HTCAPTION : HTCLIENT;
    }
    case WM_NCLBUTTONDBLCLK: return 0;
    case WM_LBUTTONUP: {
      RECT rect; GetClientRect(hwnd,&rect);
      const int x=GET_X_LPARAM(l)*width/std::max(1L,rect.right);
      const int y=GET_Y_LPARAM(l)*height/std::max(1L,rect.bottom);
      if(y>=8 && y<54) {
        if(x>=592) closeRequest();
        else if(x>=548 && x<592) ShowWindow(hwnd,SW_MINIMIZE);
      }
      return 0;
    }
    case WM_DPICHANGED: {
      auto suggested=reinterpret_cast<RECT*>(l);
      UINT dpi=HIWORD(w);
      SetWindowPos(hwnd,nullptr,suggested->left,suggested->top,MulDiv(width,dpi,96),MulDiv(height,dpi,96),SWP_NOZORDER|SWP_NOACTIVATE);
      return 0;
    }
    case WM_DESTROY: KillTimer(hwnd,1); KillTimer(hwnd,2); PostQuitMessage(0); return 0;
  }
  return DefWindowProcW(hwnd,message,w,l);
}
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE,PWSTR,int) {
  SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
  GdiplusStartupInput input; ULONG_PTR token=0;
  if(GdiplusStartup(&token,&input,nullptr)!=Ok) return 1;
  loadImage(102,brand,brandStream);
  loadImage(104,mascot,mascotStream);
  int argc=0; LPWSTR* argv=CommandLineToArgvW(GetCommandLineW(),&argc);
  int mode=0; std::wstring output;
  if(argc==3 && (wcscmp(argv[1],L"--preview")==0 || wcscmp(argv[1],L"--preview-rollback")==0
      || wcscmp(argv[1],L"--preview-cancelled")==0 || wcscmp(argv[1],L"--preview-complete")==0
      || wcscmp(argv[1],L"--verify-payload")==0)) {
    mode=wcscmp(argv[1],L"--verify-payload")==0 ? 2 : 1; output=argv[2];
    if(mode==1) { phase=installing; progressFraction=420; }
    if(wcscmp(argv[1],L"--preview-rollback")==0) { phase=stopping; rollingBack=true; progressFraction=260; }
    if(wcscmp(argv[1],L"--preview-cancelled")==0) phase=cancelled;
    if(wcscmp(argv[1],L"--preview-complete")==0) phase=complete;
  } else if(argc==2 && wcscmp(argv[1],L"--preview-window")==0) {
    previewWindow=true;
  } else if(argc!=1) {
#ifdef AZAUTHLIB_INSTALLER_TEST
    if(argc==2 && wcscmp(argv[1],L"--cancel-during-copy")==0) cancelDuringCopy=true;
    else if(argc==2 && wcscmp(argv[1],L"--fail-after-copy")==0) injectFailure=true;
    else mode=3;
#else
    mode=3;
#endif
  }
  LocalFree(argv);
  int exitCode=0;
  if(mode) exitCode=(mode==1 ? preview(output) : mode==2 ? extract(output) : false) ? 0 : 1;
  else {
    WNDCLASSW cls={}; cls.lpfnWndProc=windowProc; cls.hInstance=instance;
    cls.hIcon=LoadIconW(instance,MAKEINTRESOURCEW(1)); cls.hCursor=LoadCursorW(nullptr,IDC_ARROW);
    cls.lpszClassName=L"DOYDL.Azauthlib.NativeSetup"; RegisterClassW(&cls);
    DWORD style=WS_POPUP|WS_SYSMENU|WS_MINIMIZEBOX;
    POINT pointer={}; GetCursorPos(&pointer);
    MONITORINFO monitor={sizeof(MONITORINFO)};
    if(!GetMonitorInfoW(MonitorFromPoint(pointer,MONITOR_DEFAULTTOPRIMARY),&monitor))
      SystemParametersInfoW(SPI_GETWORKAREA,0,&monitor.rcWork,0);
    UINT dpi=GetDpiForSystem(); RECT rect={0,0,MulDiv(width,dpi,96),MulDiv(height,dpi,96)};
    AdjustWindowRectExForDpi(&rect,style,FALSE,0,dpi);
    window=CreateWindowW(cls.lpszClassName,previewWindow ? L"azauthlib Desktop Setup (Preview)" : L"azauthlib Desktop Setup",
        style,monitor.rcWork.left,monitor.rcWork.top,
        rect.right-rect.left,rect.bottom-rect.top,nullptr,nullptr,instance,nullptr);
    if(!window) exitCode=1;
    else {
      // Size on the target monitor first so mixed-DPI displays center correctly.
      dpi=GetDpiForWindow(window);
      const int w=MulDiv(width,dpi,96), h=MulDiv(height,dpi,96);
      const RECT area=monitor.rcWork;
      SetWindowPos(window,nullptr,area.left+std::max(0L,(area.right-area.left-w)/2),
          area.top+std::max(0L,(area.bottom-area.top-h)/2),w,h,SWP_NOZORDER|SWP_NOACTIVATE);
      ShowWindow(window,SW_SHOW); UpdateWindow(window);
      MSG msg; while(GetMessageW(&msg,nullptr,0,0)>0) { TranslateMessage(&msg); DispatchMessageW(&msg); }
      if(worker.joinable()) worker.join();
      exitCode=resultCode==ERROR_SUCCESS_REBOOT_REQUIRED ? 0 : static_cast<int>(resultCode);
    }
  }
  delete brand;
  if(brandStream) brandStream->Release();
  delete mascot;
  if(mascotStream) mascotStream->Release();
  GdiplusShutdown(token);
  return exitCode;
}
