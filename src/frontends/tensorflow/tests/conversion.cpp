// Copyright (C) 2018-2025 Intel Corporation
// SPDX-License-Identifier: Apache-2.0
//

#include "conversion_extension.hpp"
#include "openvino/core/so_extension.hpp"
#include "openvino/frontend/extension/telemetry.hpp"
#include "openvino/frontend/tensorflow/frontend.hpp"
#include "tf_utils.hpp"

using namespace ov::frontend;
using namespace ov::frontend::tensorflow::tests;

using TFConversionExtensionTest = FrontEndConversionExtensionTest;

static const std::string translator_name = "Relu";

class TensorflowFrontendWrapper : public ov::frontend::tensorflow::FrontEnd {
    void add_extension(const std::shared_ptr<ov::Extension>& extension) override {
        ov::frontend::tensorflow::FrontEnd::add_extension(extension);

        if (auto conv_ext = ov::as_type_ptr<ConversionExtension>(extension)) {
            if (conv_ext->get_converter() || conv_ext->get_converter_named_and_indexed()) {
                EXPECT_NE(std::find(m_conversion_extensions.begin(), m_conversion_extensions.end(), conv_ext),
                          m_conversion_extensions.end())
                    << "ConversionExtension is not registered.";
                EXPECT_NE(m_op_translators.find(conv_ext->get_op_type()), m_op_translators.end())
                    << conv_ext->get_op_type() << " translator is not registered.";
            }
        } else if (auto telemetry = std::dynamic_pointer_cast<TelemetryExtension>(extension)) {
            EXPECT_EQ(m_telemetry, telemetry) << "TelemetryExtension is not registered.";
        } else if (auto transformation = std::dynamic_pointer_cast<DecoderTransformationExtension>(extension)) {
            EXPECT_NE(std::find(m_transformation_extensions.begin(), m_transformation_extensions.end(), transformation),
                      m_transformation_extensions.end())
                << "DecoderTransformationExtension is not registered.";
        } else if (auto so_ext = std::dynamic_pointer_cast<ov::detail::SOExtension>(extension)) {
            EXPECT_NE(std::find(m_extensions.begin(), m_extensions.end(), so_ext), m_extensions.end())
                << "SOExtension is not registered.";
        }
    }
};

static ConversionExtensionFEParam getTestData() {
    ConversionExtensionFEParam res;
    res.m_frontEndName = TF_FE;
    res.m_modelsPath = std::string(TEST_TENSORFLOW_MODELS_DIRNAME);
    res.m_modelName = "2in_2out/2in_2out.pb";
    res.m_translatorName = translator_name;
    res.m_frontend = std::make_shared<TensorflowFrontendWrapper>();
    return res;
}

INSTANTIATE_TEST_SUITE_P(TFConversionExtensionTest,
                         FrontEndConversionExtensionTest,
                         ::testing::Values(getTestData()),
                         FrontEndConversionExtensionTest::getTestCaseName);
