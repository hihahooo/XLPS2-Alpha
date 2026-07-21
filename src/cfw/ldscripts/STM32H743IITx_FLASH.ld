/* STM32H743IITx Flash linker script (XLPS2-Alpha CFW)
 * 2MB Flash / 1MB SRAM (incl. 512KB DTCM + 256KB AXI + 256KB SRAM1/2/3)
 * Boot region is the running partition; A/B firmware partitions live in the
 * STM32H743 internal Flash (A=0x08020000, B=0x08100000, FLAG=0x081E0000 per
 * ADR-005). Internal Flash also holds the bootloader + param/SMDL scratch.
 * The interference library uses external FRAM via FMC/FSMC (0x60000000).
 */
MEMORY
{
  FLASH   (rx)  : ORIGIN = 0x08000000, LENGTH = 2048K
  DTCMRAM (xrw) : ORIGIN = 0x20000000, LENGTH = 512K
  ITCMRAM (xrw) : ORIGIN = 0x00000000, LENGTH = 64K
  RAM_D1  (xrw) : ORIGIN = 0x24000000, LENGTH = 512K
  RAM_D2  (xrw) : ORIGIN = 0x30000000, LENGTH = 288K
  RAM_D3  (xrw) : ORIGIN = 0x38000000, LENGTH = 64K
}

ENTRY(Reset_Handler)

_estack = ORIGIN(RAM_D1) + LENGTH(RAM_D1);

SECTIONS
{
  .isr_vector :
  {
    . = ALIGN(4);
    KEEP(*(.isr_vector))
    . = ALIGN(4);
  } >FLASH

  .text :
  {
    . = ALIGN(4);
    *(.text*)
    *(.rodata*)
    . = ALIGN(4);
  } >FLASH

  .ARM.extab   : { *(.ARM.extab* .gnu.linkonce.armextab.*) } >FLASH
  .ARM.exidx   : { *(.ARM.exidx* .gnu.linkonce.armexidx.*) } >FLASH
  .preinit_array : { . = ALIGN(4); KEEP(*(.preinit_array*)) } >FLASH
  .init_array     : { . = ALIGN(4); KEEP(*(SORT(.init_array.*)) KEEP(*(.init_array*))) } >FLASH

  _sidata = LOADADDR(.data);
  .data :
  {
    . = ALIGN(4);
    _sdata = .;
    *(.data*)
    . = ALIGN(4);
    _edata = .;
  } >RAM_D1 AT>FLASH

  .bss :
  {
    . = ALIGN(4);
    _sbss = .;
    *(.bss*)
    *(COMMON)
    . = ALIGN(4);
    _ebss = .;
  } >RAM_D1

  ._user_heap_stack (NOLOAD) :
  {
    . = ALIGN(8);
    PROVIDE( end = . );
    . = . + _Min_Heap_Size;
    . = . + _Min_Stack_Size;
    . = ALIGN(8);
  } >RAM_D1

  /DISCARD/ : { *(.note .note.*) }
}

_Min_Heap_Size  = 0x2000;
_Min_Stack_Size = 0x2000;
