// SPDX-FileCopyrightText: Copyright 2024 shadPS4 Emulator Project
// SPDX-License-Identifier: GPL-2.0-or-later

#pragma once

#include <atomic>
#include <memory>
#include <span>
#include <vector>

#include "shader_recompiler/specialization.h"
#include "video_core/renderer_vulkan/vk_common.h"
#include "video_core/renderer_vulkan/vk_pipeline_common.h"

namespace VideoCore {
class BufferCache;
class TextureCache;
} // namespace VideoCore

namespace Serialization {
struct Archive;
}

namespace Vulkan {

class Instance;
class Scheduler;
class DescriptorHeap;

struct ComputePipelineKey {
    size_t value;

    friend bool operator==(const ComputePipelineKey& lhs, const ComputePipelineKey& rhs) {
        return lhs.value == rhs.value;
    }
    friend bool operator!=(const ComputePipelineKey& lhs, const ComputePipelineKey& rhs) {
        return !(lhs == rhs);
    }

    void Serialize(Serialization::Archive& ar) const;
    bool Deserialize(Serialization::Archive& ar);
};

class ComputePipeline : public Pipeline {
public:
    struct SerializationSupport {
        u32 dummy{};

        void Serialize(Serialization::Archive& ar) const;
        bool Deserialize(Serialization::Archive& ar);
    };

    ComputePipeline(const Instance& instance, Scheduler& scheduler, DescriptorHeap& desc_heap,
                    const Shader::Profile& profile, vk::PipelineCache pipeline_cache,
                    ComputePipelineKey compute_key, const Shader::Info& info,
                    vk::ShaderModule module, SerializationSupport& sdata, bool preloading);
    ~ComputePipeline();

    /// When this pipeline temporarily stands in for a compatible compute permutation, the
    /// rasterizer compares live sampled-image types with the types this pipeline expects.
    [[nodiscard]] const std::vector<Shader::ImageSpecialization>* FallbackImages() const {
        return fallback_images_ptr.load(std::memory_order_acquire);
    }

    void SetFallbackImages(std::span<const Shader::ImageSpecialization> images) const {
        if (fallback_images_ptr.load(std::memory_order_relaxed)) {
            return;
        }
        fallback_images = std::make_unique<std::vector<Shader::ImageSpecialization>>(
            images.begin(), images.end());
        fallback_images_ptr.store(fallback_images.get(), std::memory_order_release);
    }

private:
    ComputePipelineKey compute_key;
    mutable std::unique_ptr<std::vector<Shader::ImageSpecialization>> fallback_images;
    mutable std::atomic<const std::vector<Shader::ImageSpecialization>*> fallback_images_ptr{};
};

} // namespace Vulkan

template <>
struct std::hash<Vulkan::ComputePipelineKey> {
    std::size_t operator()(const Vulkan::ComputePipelineKey& key) const noexcept {
        return std::hash<size_t>{}(key.value);
    }
};
