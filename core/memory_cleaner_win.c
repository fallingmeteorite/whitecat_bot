#include <windows.h>
#include <stdio.h>

// 模拟释放系统内存
size_t clean_memory() {
    MEMORYSTATUSEX statex;
    statex.dwLength = sizeof(statex);
    GlobalMemoryStatusEx(&statex);

    size_t freed_memory = statex.ullAvailPhys;
    printf("Windows: Freed %zu bytes of memory\n", freed_memory);
    return freed_memory;
}
