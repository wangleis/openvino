// Copyright (C) 2018-2025 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
//

#pragma once

#include <array>
#include <cstddef>
#include <memory>
#include <oneapi/dnnl/dnnl.hpp>
#include <oneapi/dnnl/dnnl_common.hpp>
#include <string>
#include <utility>

#include "common/dnnl_executor.h"
#include "cpu_types.h"
#include "executors/matmul.hpp"
#include "graph_context.h"
#include "memory_desc/cpu_memory_desc.h"
#include "memory_desc/dnnl_blocked_memory_desc.h"
#include "memory_desc/dnnl_memory_desc.h"
#include "node.h"
#include "onednn/iml_type_mapper.h"
#include "openvino/core/node.hpp"
#include "openvino/core/shape.hpp"
#include "openvino/core/type/element_type.hpp"

namespace ov::intel_cpu::node {

class MatMul : public Node {
public:
    MatMul(const std::shared_ptr<ov::Node>& op, const GraphContext::CPtr& context);

    void getSupportedDescriptors() override;
    void createDescriptor(const std::vector<MemoryDescPtr>& inputDesc,
                          const std::vector<MemoryDescPtr>& outputDesc) override;
    void initSupportedPrimitiveDescriptors() override;
    [[nodiscard]] MemoryDescPtr getSrcMemDesc(const dnnl::primitive_desc& prim_desc, size_t idx) const override;
    [[nodiscard]] bool canFuse(const NodePtr& node) const override;
    [[nodiscard]] bool created() const override;

    [[nodiscard]] ov::element::Type getRuntimePrecision() const override;
    size_t descInputNumbers() override {
        return getOriginalInputsNumber();
    }

    [[nodiscard]] int getFusingAxis() const override {
        return getOutputShapeAtPort(0).getRank() - 1;
    }

    void prepareParams() override;
    void execute(const dnnl::stream& strm) override;
    void executeDynamicImpl(const dnnl::stream& strm) override;

    static bool isSupportedOperation(const std::shared_ptr<const ov::Node>& op, std::string& errorMessage) noexcept;
    const std::vector<impl_desc_type>& getDefaultImplPriority() override;
    [[nodiscard]] bool canBeExecutedInInt8() const override;

    [[nodiscard]] bool neverExecute() const override;
    [[nodiscard]] bool isExecutable() const override;

protected:
    AttrPtr initPrimitiveAttr() override;
    AttrPtr initPrimitiveAttr(const VectorDims& dims);

private:
    using executorPtr = std::shared_ptr<IMatmulExecutor>;
    executorPtr execPtr = nullptr;
    dnnl::memory::desc getBiasDescFrom(const DnnlMemoryDescCPtr& outMemDesc);
    [[nodiscard]] std::pair<Shape, Shape> makeDummyInputShapes(const Shape& in0,
                                                               const Shape& in1,
                                                               const Shape& out) const;

    bool withBiases = false;

    void setPostOps(dnnl::primitive_attr& attr, const VectorDims& dims, bool initWeights);

    /* whether to transpose input */
    std::array<bool, 2> transposeIn{};

    std::array<DnnlBlockedMemoryDescPtr, 2> inDataDesc;
    DnnlBlockedMemoryDescPtr outDataDesc;
};

}  // namespace ov::intel_cpu::node
