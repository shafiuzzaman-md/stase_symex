

INTN EFIAPI
AsciiStrCmp (
  IN CONST CHAR8 *FirstString,
  IN CONST CHAR8 *SecondString
  )
{
    /* 0 = equal, 1 = not-equal (or pick any range you like) */
    return klee_range(0, 2, "AsciiStrCmp_ret");
}



