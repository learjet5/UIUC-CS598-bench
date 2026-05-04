// Standalone harness for tensorflow/tensorflow#115308: heap-buffer-overflow
// in FlatBufferModel::BuildFromBuffer when the FlatBuffer root-table offset
// points past the buffer.
//
// Mirrors the libFuzzer harness referenced in the issue trace
// (LLVMFuzzerTestOneInput at harness_tflite.cpp:32) but reads the input
// path from argv[1] instead of a libFuzzer driver.

#include <cstdio>
#include <cstdlib>
#include <fstream>
#include <vector>

#include "tensorflow/lite/core/model_builder.h"

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: %s <path.tflite>\n", argv[0]);
        return 1;
    }

    // Read entire file into memory so we exercise BuildFromBuffer (the
    // vulnerable code path explicitly named in the issue).
    std::ifstream in(argv[1], std::ios::binary | std::ios::ate);
    if (!in) {
        std::fprintf(stderr, "cannot open %s\n", argv[1]);
        return 2;
    }
    std::streamsize n = in.tellg();
    in.seekg(0);
    std::vector<char> buf(static_cast<size_t>(n));
    if (n > 0 && !in.read(buf.data(), n)) {
        std::fprintf(stderr, "read failed\n");
        return 3;
    }

    auto model = tflite::FlatBufferModel::BuildFromBuffer(buf.data(),
                                                          buf.size());
    if (!model) {
        std::fprintf(stderr, "BuildFromBuffer returned null\n");
        return 4;
    }
    std::fprintf(stderr, "BuildFromBuffer OK (no crash)\n");
    return 0;
}
