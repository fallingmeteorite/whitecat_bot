#include <stdlib.h>
#include <stdio.h>
#include <sys/sysinfo.h>

// 模拟释放系统内存
size_t clean_memory() {
    struct sysinfo info;
    if (sysinfo(&info) != 0) {
        perror("sysinfo");
        return 0;
    }

    size_t freed_memory = info.freeram * info.mem_unit;
    printf("Linux: Freed %zu bytes of memory\n", freed_memory);
    return freed_memory;
}
