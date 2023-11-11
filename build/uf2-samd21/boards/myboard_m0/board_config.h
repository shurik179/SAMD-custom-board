#ifndef BOARD_CONFIG_H
#define BOARD_CONFIG_H

#define VENDOR_NAME      "Island Robotics LLC"
#define PRODUCT_NAME     "My Board (M0)"
#define VOLUME_LABEL     "ROBOTBOOT"
#define INDEX_URL        "https://shurik179.github.com"

#define USB_VID          0x03EB
#define USB_PID          0x2402
#define BOARD_ID         "SAMD51G19A-MYBOARD-v0"

#define CRYSTALLESS      1

#define LED_PIN          PIN_PA17

#define BOOT_USART_MODULE           SERCOM0
#define BOOT_USART_MASK             APBAMASK
#define BOOT_USART_BUS_CLOCK_INDEX  MCLK_APBAMASK_SERCOM0
#define BOOT_USART_PAD_SETTINGS     UART_RX_PAD3_TX_PAD0
#define BOOT_USART_PAD3             PINMUX_PA07D_SERCOM0_PAD3
#define BOOT_USART_PAD2             PINMUX_UNUSED
#define BOOT_USART_PAD1             PINMUX_UNUSED
#define BOOT_USART_PAD0             PINMUX_PA04D_SERCOM0_PAD0
#define BOOT_GCLK_ID_CORE           SERCOM0_GCLK_ID_CORE
#define BOOT_GCLK_ID_SLOW           SERCOM0_GCLK_ID_SLOW
#endif
