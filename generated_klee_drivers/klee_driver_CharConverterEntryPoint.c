// Auto-generated KLEE driver for CharConverterEntryPoint
#include "global_stubs.h"
#include "global_stub_defs.c"
#include "../klee/klee.h"
#include <string.h>
#include <stdlib.h>

#include "../../edk2-testcases-main/Testcases/Sample2Tests/CharConverter/CharConverter_146_OOB_WRITE.c"

// Stub function to simulate gSmst->SmmAllocatePool
EFI_STATUS EFIAPI DummyAllocatePool(
    IN EFI_MEMORY_TYPE PoolType,
    IN UINTN Size,
    OUT VOID **Buffer
) {
    *Buffer = malloc(Size);
    klee_make_symbolic(*Buffer, Size, "SmmPoolBuffer");
    return EFI_SUCCESS;
}

EFI_STATUS EFIAPI DummyInstallProtocolInterface(
    EFI_HANDLE *Handle,
    EFI_GUID *Protocol,
    EFI_INTERFACE_TYPE InterfaceType,
    VOID *Interface
) {
    return EFI_SUCCESS;
}

int main() {
    // Stub initialization
    static EFI_SMM_SYSTEM_TABLE2 gSmstStub;
    gSmstStub.SmmAllocatePool = DummyAllocatePool;
    gSmstStub.SmmInstallProtocolInterface = DummyInstallProtocolInterface;
    gSmst = &gSmstStub;

    // Symbolic system table and image handle
    klee_make_symbolic(&gImageHandle, sizeof(gImageHandle), "gImageHandle");
    static EFI_SYSTEM_TABLE SystemTable;
    klee_make_symbolic(&SystemTable, sizeof(SystemTable), "SystemTable");
    gST = &SystemTable;

    // Directed symbolic execution for line 146 (OOB_WRITE)
    uint8_t *OutputBuffer[1];
    uint8_t InnerBuf[4];  // small to trigger OOB
    klee_make_symbolic(InnerBuf, sizeof(InnerBuf), "InnerBuf");
    OutputBuffer[0] = InnerBuf;

    CharConverterEntryPoint(gImageHandle, gST);

    return 0;
}
