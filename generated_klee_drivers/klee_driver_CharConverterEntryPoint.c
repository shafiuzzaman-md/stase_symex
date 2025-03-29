// Auto-generated KLEE driver for CharConverterEntryPoint
#include "global_stubs.h"
#include "global_stub_defs.c"
#include "../klee/klee.h"
#include <string.h>
#include <stdlib.h>
#include "../../edk2-testcases/Testcases/Sample2Tests/CharConverter/CharConverter.h"
#include "../../edk2-testcases/Testcases/Sample2Tests/CharConverter/CharConverter.c"

int main() {
    CharConverterEntryPoint(gImageHandle, gST);
    return 0;
}
