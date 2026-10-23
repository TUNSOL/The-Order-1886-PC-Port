// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once

// Compatibility for AMD FidelityFX SDK 1.1.4 when built with MinGW/Clang and libc++.
// The SDK sources were written against MSVC's CRT even though this host code is portable.

#include <cmath>
#include <cstddef>
#include <cstdio>
#include <cwchar>
#include <new>

#ifndef _countof
#define _countof(array) (sizeof(array) / sizeof((array)[0]))
#endif

template <typename... Args>
inline int swprintf_s(wchar_t* destination, std::size_t destination_size,
                      const wchar_t* format, Args... args) {
    if (!destination || destination_size == 0 || !format) {
        return -1;
    }
    const int result = std::swprintf(destination, destination_size, format, args...);
    if (result < 0 || static_cast<std::size_t>(result) >= destination_size) {
        destination[0] = L'\0';
        return -1;
    }
    return result;
}

using std::floor;
using std::log2;
