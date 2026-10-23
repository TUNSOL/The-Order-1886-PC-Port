// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <algorithm>
#include <array>
#include <cstdint>
#include <cmath>
#include <cstdlib>

namespace Vulkan::SceneResolution {
struct Size {
    uint32_t width = 1920, height = 1080;
    bool operator==(const Size&) const = default;
};
/// The Order: 1886's full scene size for a configured resolution. The retail camera renders a
/// 2.40:1 scene inside the 16:9 presentation target, so its scene height is smaller than the
/// mode's display height. The 4K experiment restores that same camera and therefore produces
/// 3840x1600 scene targets rather than 3840x2160 ones.
inline Size GameSizeForSetting(const char* value) {
    const int lines = value ? std::atoi(value) : 0;
    if (value && value[0] == 'r') {
        return {1920, 800};
    }
    return lines == 2160 ? Size{3840, 1600}
         : lines == 1080 ? Size{1920, 1080} : Size{1280, 720};
}

/// The scene targets, their reduced proxies and DLSS follow the configured game scene size.
inline Size GameSize() {
    static const Size size = GameSizeForSetting(std::getenv("BB_ORDER_RESOLUTION"));
    return size;
}
inline Size ForPreset(int preset, Size output = {}) {
    // Even dimensions for half-resolution effects; match the preset labels exactly.
    constexpr std::array<double, 5> scales{1.0, 1.5, 1.7, 2.0, 3.0};
    const double scale = scales[std::clamp(preset, 0, 4)];
    return {uint32_t(std::max(1l, std::lround(output.width / scale / 2)) * 2),
            uint32_t(std::max(1l, std::lround(output.height / scale / 2)) * 2)};
}
constexpr uint32_t Pack(Size size) { return size.width | (size.height << 16); }
constexpr Size Unpack(uint32_t packed) {
    return packed ? Size{packed & 65535u, packed >> 16} : Size{};
}
// A proxy and the guest-size image hold the same logical surface. Native shader reads
// need a resolve after proxy writes; native writes invalidate the cached proxy.
struct Coherence {
    bool valid = false, dirty = false;
    void ProxyWrite() { valid = dirty = true; }
    void CopiedToProxy() { valid = true; dirty = false; }
    void Resolved() { dirty = false; }
    void NativeWrite() { valid = dirty = false; }
};
} // namespace Vulkan::SceneResolution
