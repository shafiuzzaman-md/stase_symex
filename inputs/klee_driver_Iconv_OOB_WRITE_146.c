// Auto-generated KLEE driver template for Iconv
#include "../stase_generated/global_stubs.h"
#include "../stase_generated/global_stub_defs.c"
#include "../stase_symex/klee/klee.h"
#include <string.h>
#include <stdlib.h>

// Include the instrumented target source
#include "../stase_generated/instrumented_source/Testcases/Sample2Tests/CharConverter/CharConverter.c"

int main() {
    initialize_stubs();

    // Symbolic variables
    uint8_t InnerBuf[4];
    klee_make_symbolic(InnerBuf, sizeof(InnerBuf), "InnerBuf_4");
    uint32_t j;
    klee_make_symbolic(&j, sizeof(j), "j");
    uint32_t last;
    klee_make_symbolic(&last, sizeof(last), "last");

    // Concrete initializations
    gSmst = NULL;
    buffer_size = 0x20;

    // Call the entrypoint
    Iconv(gImageHandle, gST);

    return 0;
}
