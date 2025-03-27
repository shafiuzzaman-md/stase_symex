#define __PI_SMM_DRIVER__ 1
#include "../../edk2-testcases/MdePkg/Include/Base.h"
#include "../../edk2-testcases/MdePkg/Include/Uefi/UefiBaseType.h"
#include "../../edk2-testcases/MdePkg/Include/Uefi/UefiSpec.h"
#include "../../edk2-testcases/MdePkg/Include/Pi/PiSmmCis.h"
#include "../../edk2-testcases/MdePkg/Include/Protocol/SmmBase2.h"
#include "../../edk2-testcases/MdePkg/Include/Library/SmmServicesTableLib.h"


#include "../../edk2-testcases/MdePkg/Include/Uefi/UefiMultiPhase.h"
#include "../../edk2-testcases/BaseTools/Source/C/Include/Common/PiFirmwareVolume.h"
#include "../../edk2-testcases/MdeModulePkg/Include/Protocol/FaultTolerantWrite.h"
#include "../../edk2-testcases/MdePkg/Include/Protocol/DriverBinding.h"
#include "../../edk2-testcases/MdePkg/Include/Protocol/ComponentName.h"
#include "../../edk2-testcases/MdePkg/Include/Protocol/ComponentName2.h"
#include "../../edk2-testcases/MdePkg/Include/IndustryStandard/Pci22.h"
#include "../../edk2-testcases/MdePkg/Include/Library/BaseLib.h"
#include "../../edk2-testcases/BaseTools/Source/C/Include/Protocol/GraphicsOutput.h"
#include "../../edk2-testcases/MdeModulePkg/Bus/Pci/PciBusDxe/PciBus.h"
#include "../../edk2-testcases/MdePkg/Library/SmmMemLib/SmmMemLib.c"
#include "../../edk2-testcases/MdePkg/Library/BaseMemoryLib/CopyMemWrapper.c"
#include "../../edk2-testcases/MdePkg/Library/BaseMemoryLib/CopyMem.c"
#include "../../edk2-testcases/MdePkg/Library/BaseLib/Math64.c"
#include "../../edk2-testcases/MdePkg/Library/BaseLib/DivU64x32.c"
#include "../../edk2-testcases/StandaloneMmPkg/Library/StandaloneMmMemLib/StandaloneMmMemLib.c"
#include "../../edk2-testcases/MdeModulePkg/Library/SmmLockBoxLib/SmmLockBoxDxeLib.c"
#include "../../edk2-testcases/MdeModulePkg/Universal/Variable/RuntimeDxe/VariableRuntimeCache.c"
#include "../../edk2-testcases/MdeModulePkg/Universal/Variable/RuntimeDxe/TcgMorLockSmm.c"
#include "../../edk2-testcases/MdeModulePkg/Include/Protocol/SmmVariable.h"

#include "../klee/klee.h"
#include <string.h>
#include <stdlib.h>
#include "../../edk2-testcases/Testcases/Sample2Tests/CharConverter/CharConverter.h"

// Stubbed EFI System Table and Image Handle
EFI_SYSTEM_TABLE gSysTable;
EFI_HANDLE gImageHandle = (EFI_HANDLE)0;

VOID *EFIAPI ZeroMem(VOID *Buffer, UINTN Size) {
    return memset(Buffer, 0, Size);
}

VOID *EFIAPI AllocateZeroPool(IN UINTN Size) {
    void *ptr = malloc(Size);
    if (ptr) ZeroMem(ptr, Size);
    return ptr;
}

UINTN EFIAPI AsciiStrSize(IN CONST CHAR8 *String) {
    return (String == NULL) ? 0 : strlen(String) + 1;
}

INTN EFIAPI AsciiStrCmp(IN CONST CHAR8 *FirstString, IN CONST CHAR8 *SecondString) {
    return strcmp(FirstString, SecondString);
}

EFI_STATUS EFIAPI AsciiStrCpyS(CHAR8 *Dest, UINTN DestSize, CONST CHAR8 *Src) {
    strncpy(Dest, Src, DestSize);
    return EFI_SUCCESS;
}

EFI_STATUS EFIAPI MySmmAllocatePool(
    IN EFI_MEMORY_TYPE PoolType,
    IN UINTN Size,
    OUT VOID **Buffer
) {
    if (!Buffer) return EFI_INVALID_PARAMETER;
    *Buffer = malloc(Size);
    if (!*Buffer) return EFI_OUT_OF_RESOURCES;
    ZeroMem(*Buffer, Size);
    return EFI_SUCCESS;
}

EFI_SMM_SYSTEM_TABLE2 gSmstMock = {
    .SmmAllocatePool = MySmmAllocatePool,
    .SmmInstallProtocolInterface = NULL
};

EFI_SMM_SYSTEM_TABLE2 *gSmst = &gSmstMock;

int main() {
    CharConverterEntryPoint(gImageHandle, &gSysTable);
    return 0;
}
