#include <stdio.h>
#include <stdlib.h>

// 函数：释放给定内存地址
void clean_memory(void* ptr) {
    if (ptr == NULL) {
        printf("无效的内存地址，无法释放\n");
        return;
    }

    // 释放给定地址的内存
    free(ptr);
    printf("内存地址 %p 已被释放\n", ptr);
}