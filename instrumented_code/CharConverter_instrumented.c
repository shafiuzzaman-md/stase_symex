#include "CharConverter.h"

NOTIFY_PROTOCOL_READY_PROTOCOL      mCharConverterReady;



EFI_STATUS
EFIAPI
IconvOpen (
    IN CONST CHAR8 *ToEncoding,
    IN CONST CHAR8 *FromEncoding,
    OUT ICONV_T    *CharDesc
)
{
    CharDesc = AllocateZeroPool(sizeof(ICONV_T));
    if (CharDesc == NULL) {
        return EFI_OUT_OF_RESOURCES;
    }

    // Store encoding types
    CharDesc->FromEncoding = AllocateZeroPool(AsciiStrSize(FromEncoding));
    if (CharDesc->FromEncoding == NULL) {
        FreePool(CharDesc);
        return EFI_OUT_OF_RESOURCES;
    }
    AsciiStrCpyS(CharDesc->FromEncoding, AsciiStrSize(FromEncoding), FromEncoding);

    CharDesc->ToEncoding = AllocateZeroPool(AsciiStrSize(ToEncoding));
    if (CharDesc->ToEncoding == NULL) {
        FreePool(CharDesc->FromEncoding);
        FreePool(CharDesc);
        return EFI_OUT_OF_RESOURCES;
    }
    AsciiStrCpyS(CharDesc->ToEncoding, AsciiStrSize(ToEncoding), ToEncoding);

    return EFI_SUCCESS;
}


EFI_STATUS
EFIAPI
Iconv (
    IN ICONV_T    *CharDesc,
    IN CHAR8      *InputBuffer,
    IN UINTN  InputSize,
    OUT CHAR8     **OutputBuffer,
    IN OUT UINTN  *OutputSize
){
    if (AsciiStrCmp(CharDesc->FromEncoding, "UTF-8") == 0 &&
        AsciiStrCmp(CharDesc->ToEncoding, "UTF-16") == 0) {
        
        *OutputSize = (InputSize + 1) * sizeof(CHAR16);
        *OutputBuffer = AllocateZeroPool(*OutputSize);

        if (*OutputBuffer == NULL) {
            return EFI_OUT_OF_RESOURCES;
        }

        for (UINTN i = 0; i < InputSize; i++) {
            (*OutputBuffer)[i] = (CHAR16) InputBuffer[i]; 
        }

        (*OutputBuffer)[InputSize] = L'\0';
        return EFI_SUCCESS;

    } else if (AsciiStrCmp(CharDesc->FromEncoding, "UTF-16") == 0 &&
               AsciiStrCmp(CharDesc->ToEncoding, "UTF-8") == 0) {
        
        *OutputSize = InputSize / 2 + 1; 
        *OutputBuffer = AllocateZeroPool(*OutputSize);

        if (*OutputBuffer == NULL) {
            return EFI_OUT_OF_RESOURCES;
        }

        for (UINTN i = 0; i < InputSize / 2; i++) {
            CHAR16 *utf16_str = (CHAR16 *)InputBuffer;
            if (utf16_str[i] <= 0x7F) {
                (*OutputBuffer)[i] = (CHAR8)utf16_str[i];
            } else {
                (*OutputBuffer)[i] = '?'; 
            }
        }

        (*OutputBuffer)[InputSize / 2] = '\0';
        return EFI_SUCCESS;
    }
    else if (AsciiStrCmp(CharDesc->FromEncoding, "ISO-8859-1") == 0 &&
        AsciiStrCmp(CharDesc->ToEncoding, "UTF-16") == 0) {

        *OutputSize = (InputSize + 1) * sizeof(CHAR16);
        *OutputBuffer = AllocateZeroPool(*OutputSize);
        if (*OutputBuffer == NULL) {
            return EFI_OUT_OF_RESOURCES;
        }

        for (UINTN i = 0; i < InputSize; i++) {
            // Introducing the bug: NO boundary check in this block!
            if (i >= *OutputSize / sizeof(CHAR16)) {
                // BUG: No boundary check or buffer limit enforcement
                // This will result in buffer overflow if inbuf_size is too large
                break;
            }

            if ((InputBuffer[i] & 0x80) == 0) {
                // Standard ISO-8859-1 to UTF-16 mapping
// [OOB_WRITE] Auto-inserted assertion
klee_assert(i < (*OutputSize / sizeof(CHAR16))); // OOB check
(*OutputBuffer)[i] = (CHAR16)InputBuffer[i];
                (*OutputBuffer)[i] = (CHAR16)InputBuffer[i];
            } else {
                // Conversion for characters >= 0x80
                (*OutputBuffer)[i] = 0xFD;  // Replacement character for invalid bytes
            }
        }

        (*OutputBuffer)[InputSize] = L'\0';
        return EFI_SUCCESS;
    }

    return EFI_UNSUPPORTED;
}

EFI_STATUS
EFIAPI
StandardConvert(
    IN CHAR8 *Input,
    IN UINTN Size,
    IN HEAP_MANAGER_PROTOCOL *HeapManagerProtocol
) {
    ICONV_T *cd = NULL;
    EFI_STATUS Status = IconvOpen("ISO-8859-1", "UTF-8", cd);
    CHUNK_T *Output = NULL;

    if (Size <= BLOCK_080){
        HeapManagerProtocol->AllocateChunk(B_080, Output);
    }
    else if (Size <= BLOCK_100){
        HeapManagerProtocol->AllocateChunk(B_100, Output);
    }
    else if (Size <= BLOCK_200){
        HeapManagerProtocol->AllocateChunk(B_200, Output);
    }
    else {
        DEBUG((DEBUG_ERROR, "...input is too large, giving up\n"));
        return EFI_INVALID_PARAMETER;
    }
    if (EFI_ERROR(Status))
        return Status;
    UINTN OutputSize = Size;
    CHAR8 *InputPtr = Input;
    CHAR8 *OutputPtr = (CHAR8 *)Output;
    Status = Iconv(cd, InputPtr, Size, &OutputPtr, &OutputSize);
    if(EFI_ERROR(Status))
        return EFI_ABORTED;

    return Status;
}

EFI_STATUS
EFIAPI
Libxml2Convert(
    IN CHAR8 *Input,
    IN UINTN Size,
    IN HEAP_MANAGER_PROTOCOL *HeapManagerProtocol
) {
    ICONV_T *cd = NULL;
    EFI_STATUS Status = IconvOpen("ISO-8859-1", "UTF-8", cd);
    CHUNK_T *Output = NULL;

    if (Size*2 <= BLOCK_080){
        HeapManagerProtocol->AllocateChunk(B_080, Output);
    }
    else if (Size*2 <= BLOCK_100){
        HeapManagerProtocol->AllocateChunk(B_100, Output);
    }
    else if (Size*2 <= BLOCK_200){
        HeapManagerProtocol->AllocateChunk(B_200, Output);
    }
    else {
        DEBUG((DEBUG_ERROR, "...input is too large, giving up\n"));
        return EFI_INVALID_PARAMETER;
    }
    if (EFI_ERROR(Status))
        return Status;
    UINTN OutputSize = Size*2;
    CHAR8 *InputPtr = Input;
    CHAR8 *OutputPtr = (CHAR8 *)Output;
    Status = Iconv(cd, InputPtr, Size, &OutputPtr, &OutputSize);
    if(EFI_ERROR(Status))
        return EFI_ABORTED;

    return Status;
}

EFI_STATUS
EFIAPI
PkexecConvert(
    IN CHAR8 *Input,
    IN UINTN Size,
    IN HEAP_MANAGER_PROTOCOL *HeapManagerProtocol
) {
    ICONV_T *cd = NULL;
    EFI_STATUS Status = IconvOpen("ISO-8859-1", "UTF-8", cd);
    CHUNK_T *Output = NULL;

    if (Size + NUL_TERMINATOR_LENGTH <= BLOCK_080){
        HeapManagerProtocol->AllocateChunk(B_080, Output);
    }
    else if (Size + NUL_TERMINATOR_LENGTH <= BLOCK_100){
        HeapManagerProtocol->AllocateChunk(B_100, Output);
    }
    else if (Size + NUL_TERMINATOR_LENGTH <= BLOCK_200){
        HeapManagerProtocol->AllocateChunk(B_200, Output);
    }
    else {
        DEBUG((DEBUG_ERROR, "...input is too large, giving up\n"));
        return EFI_INVALID_PARAMETER;
    }
    if (EFI_ERROR(Status))
        return Status;
    UINTN OutputSize = Size + NUL_TERMINATOR_LENGTH;
    CHAR8 *InputPtr = Input;
    CHAR8 *OutputPtr = (CHAR8 *)Output;
    Status = Iconv(cd, InputPtr, Size, &OutputPtr, &OutputSize);
    if(EFI_ERROR(Status))
        return EFI_ABORTED;

    return Status;
}

EFI_STATUS
EFIAPI
CharConverterEntryPoint(
    IN EFI_HANDLE       ImageHandle,
    IN EFI_SYSTEM_TABLE *SystemTable
)
{
    EFI_STATUS Status;
    EFI_HANDLE HandleProtoc = NULL;
    EFI_HANDLE HandleNotify = NULL;
    CHAR_CONVERTER_PROTOCOL *mCharConverter;
    UINTN      ProtocolSize = sizeof(CHAR_CONVERTER_PROTOCOL);
    
    //
    //
    // Allocate a memory pool for the protocol
    Status = gSmst->SmmAllocatePool(
                    EfiRuntimeServicesData,
                    ProtocolSize,
                    (VOID **)&mCharConverter
                    );
    if (EFI_ERROR (Status)) {
        return Status;
    }

    //
    //
    // Initialize the protocol instance
    mCharConverter->IconvOpen = IconvOpen;
    mCharConverter->Iconv = Iconv;
    mCharConverter->StandardConvert = StandardConvert;
    mCharConverter->Libxml2Convert = Libxml2Convert;
    mCharConverter->PkexecConvert = PkexecConvert;

    //
    //
    // Install the protocol
    Status = gSmst->SmmInstallProtocolInterface(
                        &HandleProtoc,
                        &gEfiCharConverterProtocolGuid,
                        EFI_NATIVE_INTERFACE,
                        mCharConverter
                        );
    if (EFI_ERROR (Status)) {
        return Status;
    }

    mCharConverterReady.ReadyFlags = ~(0x00);
    Status = gSmst->SmmInstallProtocolInterface(
                    &HandleNotify,
                    &gEfiCharConverterReadyProtocolGuid,
                    EFI_NATIVE_INTERFACE,
                    &mCharConverterReady
                    );
    if (EFI_ERROR (Status)) {
        return Status;
    }

    return Status;
}