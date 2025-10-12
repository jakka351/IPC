#include "pch.h"
#include <memory>
#include <cstdlib>
#include <stdio.h>
#include <iostream>
#include <sstream>
#include <string>
#include <math.h>
#include <tchar.h>
#include <stdlib.h>
#include <windows.h>
#include <map>
#include <array>


namespace lzss
{
    typedef uint8_t BYTE;     // BYTE = unsigned 8 bit value
    typedef uint16_t WORD;    // WORD = unsigned 16 bit value

    //The following defines were taken from https://github.com/nihilus/hexrays_tools/blob/master/code/defs.h. 

    #define _BYTE  uint8_t
    #define _WORD  uint16_t
    #define _DWORD uint32_t

    #define LOWORD(x)   (*((_WORD*)&(x)))   // low word
    #define HIWORD(x)   (*((_WORD*)&(x)+1))
    #define BYTEn(x, n)   (*((_BYTE*)&(x)+n))
    #define WORDn(x, n)   (*((_WORD*)&(x)+n))

    #define BYTE2(x)   BYTEn(x,  2)
    #define BYTE3(x)   BYTEn(x,  3)


    struct TreeNode;
    struct LzssContext;
    LzssContext* InitLzssContext();
    LzssContext* __cdecl lzss_compress_data(unsigned __int8* input_buffer, unsigned int input_length);//, unsigned __int8* output_buffer);
    LzssContext* __cdecl output_bits(unsigned int bits, unsigned __int8 num_bits, LzssContext* ctx);

    extern "C" __declspec(dllexport) void freeMemory();

    LzssContext* __cdecl lzss_init_tree(unsigned __int16 root_child, LzssContext* ctx);
    LzssContext* __cdecl lzss_contract_node(unsigned __int16 old_node, unsigned __int16 new_node, LzssContext* ctx);
    LzssContext* __cdecl lzss_replace_node(unsigned __int16 old_node, unsigned __int16 new_node, LzssContext* ctx);
    unsigned __int16 __cdecl lzss_find_next_node(unsigned __int16 node, LzssContext* ctx);
    LzssContext* __cdecl lzss_delete_node(unsigned __int16 node, LzssContext* ctx);
    LzssContext* __cdecl lzss_add_node(unsigned __int16 new_node, unsigned __int16* match_pos, unsigned __int8 lzss_window[], LzssContext* ctx);

    struct TreeNode
    {
        unsigned __int16 parent;
        unsigned __int16 small_child;
        unsigned __int16 large_child;
    };

    struct LzssContext
    {
        unsigned __int8 bCompressedData[0x500000];
        unsigned __int8 out_bit; //= 128u; // idb
        unsigned int out_len; // idb
        unsigned __int8 in_bit; // = 128u; // idb
        unsigned __int8 lzss_window[1024]; // idb
        unsigned __int8* out_ptr; // idb
        unsigned __int8 match_len; // [sp+12h] [bp-Eh]@1
        TreeNode tree[1025];
    };

    extern "C" __declspec(dllexport) unsigned char* CompressBlock(unsigned char* uncompressedData, int uncompressedLength, int* compressedDataSize)
    {
        //std::allocator<unsigned __int8> alloc;
        //unsigned __int8* compressedData = alloc.allocate(uncompressedLength);
        //memset(compressedData, 0, uncompressedLength)
        //Put compression alg here
        //globalVarTest = compressedData;
        //ctx = InitLzssContext();
    
        LzssContext* ctx2 = lzss_compress_data(uncompressedData, uncompressedLength);
        *compressedDataSize = ctx2->out_len;
        return ctx2->bCompressedData;
    }

    // Using a single, statically allocated LzssContext
    // Not thread safe
    LzssContext* InitLzssContext()
    {
        static LzssContext ctx; // statically allocated, persists across calls

        // Zero out the entire structure
        memset(&ctx, 0, sizeof(ctx));

        // Initialize the necessary fields
        ctx.out_ptr = ctx.bCompressedData;
        ctx.out_bit = 128u;
        ctx.in_bit = 128u;
        ctx.match_len = 0;

        return &ctx;
    }



    LzssContext* __cdecl lzss_init_tree(unsigned __int16 root_child, LzssContext* ctx)
    {
        ctx->tree[1024].parent = 0;
        ctx->tree[1024].small_child = 0;
        ctx->tree[1024].large_child = root_child;
        ctx->tree[root_child].parent = 1024;
        ctx->tree[root_child].large_child = 0;
        ctx->tree[root_child].small_child = 0;
        return ctx;
    }

    LzssContext* __cdecl lzss_contract_node(unsigned __int16 old_node, unsigned __int16 new_node, LzssContext* ctx)
    {
        ctx->tree[new_node].parent = ctx->tree[old_node].parent;
        if (ctx->tree[ctx->tree[old_node].parent].large_child == old_node)
            ctx->tree[ctx->tree[old_node].parent].large_child = new_node;
        else
            ctx->tree[ctx->tree[old_node].parent].small_child = new_node;
        ctx->tree[old_node].parent = 0;
        ctx->tree[old_node].small_child = 0;
        ctx->tree[old_node].large_child = 0;
        return ctx;
    }

    LzssContext* __cdecl lzss_replace_node(unsigned __int16 old_node, unsigned __int16 new_node, LzssContext* ctx)
    {
        TreeNode* v2; // edx@4
        TreeNode* v3; // eax@4

        if (ctx->tree[ctx->tree[old_node].parent].small_child == old_node)
            ctx->tree[ctx->tree[old_node].parent].small_child = new_node;
        else
            ctx->tree[ctx->tree[old_node].parent].large_child = new_node;
        v2 = &(ctx->tree[new_node]);
        v3 = &(ctx->tree[old_node]);
        *(_DWORD*)&v2->parent = *(_DWORD*)&v3->parent;

        v2->large_child = v3->large_child;
        ctx->tree[ctx->tree[new_node].small_child].parent = new_node;
        ctx->tree[ctx->tree[new_node].large_child].parent = new_node;
        ctx->tree[old_node].parent = 0;
        ctx->tree[old_node].small_child = 0;
        ctx->tree[old_node].large_child = 0;
        return ctx;
    }

    unsigned __int16 __cdecl lzss_find_next_node(unsigned __int16 node, LzssContext* ctx)
    {
        unsigned __int16 next; // [sp+12h] [bp-2h]@1

        for (next = ctx->tree[node].small_child; ctx->tree[next].large_child; next = ctx->tree[next].large_child)
            ;
        return next;
    }

    LzssContext* __cdecl lzss_delete_node(unsigned __int16 node, LzssContext* ctx)
    {
        unsigned __int16 repl_node; // ST1A_2@5

        if (ctx->tree[node].large_child)
        {
            if (ctx->tree[node].small_child)
            {
                repl_node = lzss_find_next_node(node, ctx);
                ctx = lzss_contract_node(repl_node, ctx->tree[repl_node].small_child, ctx);
                ctx = lzss_replace_node(node, repl_node, ctx);
            }
            else
            {
                ctx = lzss_contract_node(node, ctx->tree[node].large_child, ctx);
            }
        }
        else
        {
            ctx = lzss_contract_node(node, ctx->tree[node].small_child, ctx);
        }
    
        return ctx;
    }

    LzssContext* __cdecl lzss_add_node(unsigned __int16 new_node, unsigned __int16* match_pos, unsigned __int8 lzss_window[], LzssContext* ctx)
    {
        unsigned __int8 result; // al@2
        unsigned __int8 ret_val; // [sp+Eh] [bp-Eh]@1
        unsigned __int8 match_done; // [sp+Fh] [bp-Dh]@1
        char* child; // [sp+10h] [bp-Ch]@15
        unsigned __int8 match_len; // [sp+15h] [bp-7h]@3
        __int16 delta; // [sp+16h] [bp-6h]@4
        unsigned __int16 test_node; // [sp+18h] [bp-4h]@3
        unsigned __int8 test_node_3; // [sp+1Bh] [bp-1h]@4

        match_done = 0;
        ret_val = 0;
        if (new_node)
        {
            test_node = ctx->tree[1024].large_child;
            match_len = 0;
            while (!match_done)
            {
                test_node_3 = 0;
                delta = 0;
                while (test_node_3 <= 0x10u && !delta)
                {
                    delta = lzss_window[(new_node + test_node_3) & 0x3FF] - lzss_window[(test_node + test_node_3) & 0x3FF];
                    ++test_node_3;
                }
                if (delta)
                    --test_node_3;
                if (test_node_3 >= match_len)
                {
                    match_len = test_node_3;
                    *match_pos = test_node;
                    if (test_node_3 > 0x10u)
                    {
                        ctx = lzss_replace_node(test_node, new_node, ctx);
                        ctx->match_len = test_node_3;
                        match_done = 1;
                    }
                }
                if (!match_done)
                {
                    if (delta < 0)
                        child = (char*)&ctx->tree[test_node].small_child;
                    else
                        child = (char*)&ctx->tree[test_node].large_child; //This may screw up
                    if (!*(_WORD*)child)
                    {
                        *(_WORD*)child = new_node;
                        ctx->tree[new_node].parent = test_node;
                        ctx->tree[new_node].large_child = 0;
                        ctx->tree[new_node].small_child = 0;
                        ctx->match_len = match_len;
                        match_done = 1;
                    }
                    test_node = *(_WORD*)child;
                }
            }
            //result = ret_val;
        }
        else
        {
            ctx->match_len = 0;
        }
        return ctx;
    }

    LzssContext* __cdecl output_bits(unsigned int bits, unsigned __int8 num_bits, LzssContext* ctx)
    {
        unsigned __int8 num_bitsa; // [sp+0h] [bp-18h]@1
        unsigned int bit_value; // [sp+10h] [bp-8h]@1

        num_bitsa = num_bits;
        bit_value = 1 << (num_bits - 1);
        while (num_bitsa)
        {
            if (ctx->out_bit == -128)
                *(ctx->out_ptr) = 0;
            if (bits & bit_value)
                *(ctx->out_ptr) |= ctx->out_bit;
            if (ctx->out_bit == 1)
            {
                ctx->out_bit = -128;
                ++(ctx->out_ptr);
                ++(ctx->out_len);
                //++out_ptr;
                //++out_len;
            }
            else
            {
                ctx->out_bit >>= 1;
            }
            bit_value >>= 1;
            --num_bitsa;
        }
        return ctx;
    }

        //unsigned __int8 bCompressedData[621156]; //this works
        //std::allocator<unsigned __int8> alloc;
        //unsigned __int8* compressedData;


    extern "C" __declspec(dllexport) void freeMemory()
    {
        //delete[] globalVarTest;
        //Trying to free the global memory since exception errors are thrown (I think) because of the repeated calls to CompressBlockNew
        //free(globalVarTest);
        return;
    }

    LzssContext* __cdecl lzss_compress_data(unsigned __int8* input_buffer, unsigned int input_length) //unsigned __int8* output_buffer)
    {
        int match_pos; // [sp+Ch] [bp-14h]@1
        unsigned __int8 eos_reached; // [sp+11h] [bp-Fh]@1
        unsigned __int8 repl_cnt; // [sp+13h] [bp-Dh]@1
        int win_pos; // [sp+14h] [bp-Ch]@1
        unsigned __int8* in_ptr; // idb

        LzssContext* ctx = InitLzssContext();

        if(SecurityOK() != TRUE)
        {
            return ctx;
        }

        unsigned __int8 lzss_window[1024]; // idb
        win_pos = 1;
        repl_cnt = 0;
        //match_len = 0;
        match_pos = 0;
        eos_reached = 0;
        in_ptr = input_buffer;

        unsigned __int8* output_buffer = ctx->out_ptr;

        ctx->out_bit = -128;
        ctx->out_len = 0;

        memset(lzss_window, 0, sizeof(lzss_window));
        memset(ctx->tree, 0, sizeof(ctx->tree));

        while (BYTE2(win_pos) <= 0x10u && !eos_reached)
        {
            HIWORD(match_pos) = *in_ptr++;
            if (in_ptr - input_buffer <= input_length)
            {
                *(&lzss_window[BYTE2(win_pos)] + (unsigned __int16)win_pos) = BYTE2(match_pos);
                ++BYTE2(win_pos);
            }
            else
            {
                eos_reached = 1;
            }
        }
        ctx = lzss_init_tree(win_pos, ctx); //The value of this is 1114113 each time it is called

        while (BYTE2(win_pos))
        {
            if (ctx->match_len > BYTE2(win_pos))
                ctx->match_len = BYTE2(win_pos);
            if (ctx->match_len > 1u)
            {
                ctx = output_bits(0, 1u, ctx);
                ctx = output_bits((unsigned __int16)match_pos, 0xAu, ctx);
                ctx = output_bits(ctx->match_len - 2, 4u, ctx);
                repl_cnt = ctx->match_len;
            }
            else
            {
                repl_cnt = 1;
                ctx = output_bits(1u, 1u, ctx);
                ctx = output_bits(lzss_window[(unsigned __int16)win_pos], 8u, ctx);
            }
            for (BYTE3(win_pos) = 0; BYTE3(win_pos) < repl_cnt; ++BYTE3(win_pos))
            {
                ctx = lzss_delete_node((win_pos + 17) & 0x3FF, ctx);
                HIWORD(match_pos) = *in_ptr++;
                if (in_ptr - input_buffer <= input_length)
                    lzss_window[((_WORD)win_pos + 17) & 0x3FF] = BYTE2(match_pos);
                else
                    --BYTE2(win_pos);
                LOWORD(win_pos) = (win_pos + 1) & 0x3FF;
                if (BYTE2(win_pos))
                    ctx = lzss_add_node(win_pos, (unsigned __int16*)&match_pos, lzss_window, ctx);
            }
        }
        ctx = output_bits(0, 1u, ctx);
        ctx = output_bits(0, 0xAu, ctx);
        output_buffer[(ctx->out_len)++] = 0;
        return ctx;
    }
}