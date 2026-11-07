// Copyright 2024 DOYDL Technologies. Licensed under the Apache License, Version 2.0.
#include "windows_progress.h"
#include <cassert>
#include <climits>

int main() {
  InstallerProgress p;
  p.update(2,100);
  p.actionData();
  assert(p.fraction()==-1);
  p.update(0,1000);
  assert(p.fraction()==0);
  p.update(2,200);
  assert(p.fraction()==200);
  p.update(1,10,1);
  p.actionData();
  assert(p.fraction()==210);
  p.update(1,100,0);
  p.actionData();
  assert(p.fraction()==210);
  p.update(3,1000);
  assert(p.fraction()==105);
  p.update(2,5000);
  assert(p.fraction()==1000);
  p.update(0,100,1);
  assert(p.backwards && p.fraction()==1000);
  p.update(2,20);
  assert(p.fraction()==800);
  p.update(1,5,1);
  p.actionData();
  assert(p.fraction()==750);
  p.update(2,1000);
  assert(p.fraction()==0);
  p.update(0,0);
  assert(p.fraction()==-1);
  p.update(0,INT_MAX);
  p.update(3,INT_MAX);
  p.update(2,INT_MAX);
  assert(p.fraction()==500);
  p.update(2,-100);
  assert(p.fraction()==500);
}
