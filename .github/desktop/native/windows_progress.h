// Copyright 2024 DOYDL Technologies. Licensed under the Apache License, Version 2.0.
#pragma once
#include <algorithm>
#include <cstdint>

// MSI reports progress for its current execution stage, including reverse
// progress during rollback. Do not infer elapsed time from these estimates.
struct InstallerProgress {
  std::int64_t total = 0, position = 0, actionTicks = 0;
  bool initialized = false, backwards = false;

  void update(int type, int ticks, int direction = 0) {
    const auto count = std::max(0, ticks);
    if(type == 0) {
      total = count;
      backwards = direction == 1;
      position = backwards ? total : 0;
      actionTicks = 0;
      initialized = true;
    } else if(initialized) {
      if(type == 1) actionTicks = direction == 1 ? count : 0;
      else if(type == 2) advance(count);
      else if(type == 3) total += count;
    }
  }
  void advance(std::int64_t ticks) {
    position = std::clamp(position + (backwards ? -ticks : ticks), std::int64_t(0), total);
  }
  void actionData() {
    if(initialized) advance(actionTicks);
  }
  int fraction() const {
    return initialized && total > 0 ? static_cast<int>(position * 1000 / total) : -1;
  }
};
