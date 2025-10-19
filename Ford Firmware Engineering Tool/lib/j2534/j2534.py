#region Copyright (c) 2024, Jack Leighton
# /////     __________________________________________________________________________________________________________________
# /////
# /////                  __                   __              __________                                      __   
# /////                _/  |_  ____   _______/  |_  __________\______   \_______   ____   ______ ____   _____/  |_ 
# /////                \   __\/ __ \ /  ___/\   __\/ __ \_  __ \     ___/\_  __ \_/ __ \ /  ___// __ \ /    \   __\
# /////                 |  | \  ___/ \___ \  |  | \  ___/|  | \/    |     |  | \/\  ___/ \___ \\  ___/|   |  \  |  
# /////                 |__|  \___  >____  > |__|  \___  >__|  |____|     |__|    \___  >____  >\___  >___|  /__|  
# /////                           \/     \/            \/                             \/     \/     \/     \/      
# /////                                                          .__       .__  .__          __                    
# /////                               ____________   ____   ____ |__|____  |  | |__| _______/  |_                  
# /////                              /  ___/\____ \_/ __ \_/ ___\|  \__  \ |  | |  |/  ___/\   __\                 
# /////                              \___ \ |  |_> >  ___/\  \___|  |/ __ \|  |_|  |\___ \  |  |                   
# /////                             /____  >|   __/ \___  >\___  >__(____  /____/__/____  > |__|                   
# /////                                  \/ |__|        \/     \/        \/             \/                         
# /////                                  __                         __  .__                                        
# /////                   _____   __ ___/  |_  ____   _____   _____/  |_|__|__  __ ____                            
# /////                   \__  \ |  |  \   __\/  _ \ /     \ /  _ \   __\  \  \/ // __ \                           
# /////                    / __ \|  |  /|  | (  <_> )  Y Y  (  <_> )  | |  |\   /\  ___/                           
# /////                   (____  /____/ |__|  \____/|__|_|  /\____/|__| |__| \_/  \___  >                          
# /////                        \/                         \/                          \/                           
# /////                                                  .__          __  .__                                      
# /////                                       __________ |  |  __ ___/  |_|__| ____   ____   ______                
# /////                                      /  ___/  _ \|  | |  |  \   __\  |/  _ \ /    \ /  ___/                
# /////                                      \___ (  <_> )  |_|  |  /|  | |  (  <_> )   |  \\___ \                 
# /////                                     /____  >____/|____/____/ |__| |__|\____/|___|  /____  >                
# /////                                          \/                                      \/     \/                 
# /////                                   Tester Present Specialist Automotive Solutions
# /////     __________________________________________________________________________________________________________________
# /////      |--------------------------------------------------------------------------------------------------------------|
# /////      |       https://github.com/jakka351/| https://testerPresent.com.au | https://facebook.com/testerPresent        |
# /////      |--------------------------------------------------------------------------------------------------------------|
# /////      | Copyright (c) 2022/2023/2024 Benjamin Jack Leighton                                                          |          
# /////      | All rights reserved.                                                                                         |
# /////      |--------------------------------------------------------------------------------------------------------------|
# /////        Redistribution and use in source and binary forms, with or without modification, are permitted provided that
# /////        the following conditions are met:
# /////        1.    With the express written consent of the copyright holder.
# /////        2.    Redistributions of source code must retain the above copyright notice, this
# /////              list of conditions and the following disclaimer.
# /////        3.    Redistributions in binary form must reproduce the above copyright notice, this
# /////              list of conditions and the following disclaimer in the documentation and/or other
# /////              materials provided with the distribution.
# /////        4.    Neither the name of the organization nor the names of its contributors may be used to
# /////              endorse or promote products derived from this software without specific prior written permission.
# /////      _________________________________________________________________________________________________________________
# /////      THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
# /////      INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# /////      DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# /////      SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# /////      SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY,
# /////      WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE
# /////      USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
# /////      _________________________________________________________________________________________________________________
# /////
# /////       This software can only be distributed with my written permission. It is for my own educational purposes and  
# /////       is potentially dangerous to ECU health and safety. Gracias a Gato Blancoford desde las alturas del mar de chelle.                                                        
# /////      _________________________________________________________________________________________________________________
# /////
# /////
# ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#endregion License
# ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

import ctypes
from ctypes import *
from enum import IntEnum, IntFlag
from typing import List, Optional
import sys

# ===== ctypes typedefs (portable, 32/64-bit) =====
import ctypes as _ct

# Exact-width unsigned/signed
UINT8   = _ct.c_uint8
UINT16  = _ct.c_uint16
UINT32  = _ct.c_uint32
UINT64  = _ct.c_uint64
INT8    = _ct.c_int8
INT16   = _ct.c_int16
INT32   = _ct.c_int32
INT64   = _ct.c_int64

# Win-isms / common aliases used by J2534 headers & wrappers
BYTE    = UINT8
WORD    = UINT16
DWORD   = UINT32
ULONG   = UINT32
LONG    = INT32
UINT    = _ct.c_uint
INT     = _ct.c_int
BOOL    = _ct.c_int      # J2534 API treats BOOL as 32-bit

CHAR    = _ct.c_char
UCHAR   = _ct.c_ubyte
WCHAR   = _ct.c_wchar

# Pointer-sized integers (portable across 32/64-bit Python)
if _ct.sizeof(_ct.c_void_p) == 8:
    INTPTR   = _ct.c_int64
    UINTPTR  = _ct.c_uint64
else:
    INTPTR   = _ct.c_int32
    UINTPTR  = _ct.c_uint32

ULONG_PTR  = UINTPTR
DWORD_PTR  = UINTPTR
SIZE_T     = _ct.c_size_t
LPVOID     = _ct.c_void_p
PVOID      = _ct.c_void_p
HANDLE     = _ct.c_void_p

# Export the typedefs so other modules (j2534_struct.py) can import them
__all__ = [
    # exact width
    "UINT8","UINT16","UINT32","UINT64","INT8","INT16","INT32","INT64",
    # aliases
    "BYTE","WORD","DWORD","ULONG","LONG","UINT","INT","BOOL","CHAR","UCHAR","WCHAR",
    # pointer-sized
    "INTPTR","UINTPTR","ULONG_PTR","DWORD_PTR","SIZE_T","LPVOID","PVOID","HANDLE",
]



# ///////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
class ConfigParameter(IntEnum):
    DATA_RATE = 0x01
    LOOPBACK = 0x03
    NODE_ADDRESS = 0x04
    NETWORK_LINE = 0x05
    P1_MIN = 0x06
    P1_MAX = 0x07
    P2_MIN = 0x08
    P2_MAX = 0x09
    P3_MIN = 0x0A
    P3_MAX = 0x0B
    P4_MIN = 0x0C
    P4_MAX = 0x0D
    W1 = 0x0E
    W2 = 0x0F
    W3 = 0x10
    W4 = 0x11
    W5 = 0x12
    TIDLE = 0x13
    TINIL = 0x14
    TWUP = 0x15
    PARITY = 0x16
    BIT_SAMPLE_POINT = 0x17
    SYNC_JUMP_WIDTH = 0x18
    W0_MIN = 0x19
    T1_MAX = 0x1A
    T2_MAX = 0x1B
    T4_MAX = 0x1C
    T5_MAX = 0x1D
    ISO15765_BS = 0x1E
    ISO15765_STMIN = 0x1F
    DATA_BITS = 0x20
    FIVE_BAUD_MOD = 0x21
    BS_TX = 0x22
    STMIN_TX = 0x23
    T3_MAX = 0x24
    ISO15765_WFT_MAX = 0x25
    W1_MIN = 0X26
    W2_MIN = 0X27
    W3_MIN = 0X28
    W4_MAX = 0X29
    N_BR_MIN = 0X2A
    ISO15765_PAD_VALUE = 0X2B
    N_AS_MAX = 0X2C
    N_AR_MAX = 0X2D
    N_BS_MAX = 0X2E
    N_CR_MAX = 0X2F
    N_CS_MIN = 0X30
    ECHO_PHYSCIAL_CHANNEL_TX = 0X31
    CAN_MIXED_FORMAT = 0x00008000
    J1962_PINS = 0x00008001
    SW_CAN_HS_DATA_RATE = 0x00008010
    SW_CAN_SPEEDCHANGE_ENABLE = 0x00008011
    SW_CAN_RES_SWITCH = 0x00008012
    ACTIVE_CHANNELS = 0x00008020
    SAMPLE_RATE = 0x00008021
    SAMPLES_PER_READING = 0x00008022
    READINGS_PER_MSG = 0x00008023
    AVERAGING_METHOD = 0x00008024
    SAMPLE_RESOLUTION = 0x00008025
    INPUT_RANGE_LOW = 0x00008026
    INPUT_RANGE_HIGH = 0x00008027
    UEB_T0_MIN = 0x00008028
    UEB_T1_MAX = 0x00008029
    UEB_T2_MAX = 0x0000802A
    UEB_T3_MAX = 0x0000802B
    UEB_T4_MIN = 0x0000802C
    UEB_T5_MAX = 0x0000802D
    UEB_T6_MAX = 0x0000802E
    UEB_T7_MIN = 0x0000802F
    UEB_T7_MAX = 0x00008030
    UEB_T9_MIN = 0x00008031
    J1939_PINS = 0x0000803D
    J1708_PINS = 0x0000803E
    J1939_T1 = 0x0000803F
    J1939_T2 = 0x00008040
    J1939_T3 = 0x00008041
    J1939_T4 = 0x00008042
    J1939_BRDCST_MIN_DELAY = 0x00008043
    TP2_0_T_BR_INT = 0x00008044
    TP2_0_T_E = 0x00008045
    TP2_0_MNTC = 0x00008046
    TP2_0_T_CTA = 0x00008047
    TP2_0_MNCT = 0x00008048
    TP2_0_MNTB = 0x00008049
    TP2_0_MNT = 0x0000804A
    TP2_0_T_Wait = 0x0000804B
    TP2_0_T1 = 0x0000804C
    TP2_0_T3 = 0x0000804D
    TP2_0_IDENTIFER = 0x0000804E
    TP2_0_RXIDPASSIVE = 0x0000804F
    OBDX_DelayBetweenCANFrames = 0x00010000  # in MICROSECONDS. Default is 500uS
    OBDX_FlowControlDelayMessage = 0x00010001  # in micros. Default is 1mS as of v1.03


class IJ2534:
    """Interface for J2534 functions"""
    
    def load_library(self, device: 'J2534Device') -> bool:
        raise NotImplementedError
    
    def free_library(self) -> bool:
        raise NotImplementedError
    
    def pass_thru_open(self, name: c_void_p, device_id: c_uint) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_close(self, device_id: c_uint) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_connect(self, device_id: c_uint, protocol_id: 'ProtocolID', 
                         flags: 'ConnectFlag', baud_rate: 'BaudRate', 
                         channel_id: c_uint) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_disconnect(self, channel_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_read_msgs(self, channel_id: c_int, msgs: c_void_p, 
                           num_msgs: c_int, timeout: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_start_periodic_msg(self, channel_id: c_int, msg: c_void_p, 
                                    msg_id: c_int, time_interval: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_stop_periodic_msg(self, channel_id: c_int, msg_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_start_msg_filter(self, channel_id: c_int, filter_type: 'FilterType',
                                  mask_msg: c_void_p, pattern_msg: c_void_p,
                                  flow_control_msg: c_void_p, filter_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_stop_msg_filter(self, channel_id: c_int, filter_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_set_programming_voltage(self, device_id: c_int, 
                                         pin_number: 'PinNumber', 
                                         voltage: c_uint) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_read_version(self, device_id: c_int, firmware_version: c_void_p,
                              dll_version: c_void_p, api_version: c_void_p) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_get_last_error(self, error_description: c_void_p) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_ioctl(self, channel_id: c_int, ioctl_id: c_int,
                       input_ptr: c_void_p, output_ptr: c_void_p) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_queue_msgs(self, channel_id: c_int, msg: c_void_p, 
                            num_msgs: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_scan_for_devices(self, device_count: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_get_next_device(self, device: 'SDEVICE') -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_logical_connect(self, physical_channel_id: c_int, 
                                 protocol_id: 'ProtocolID', flags: 'ConnectFlag',
                                 channel_descriptor: c_void_p, 
                                 logical_channel_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_logical_disconnect(self, logical_channel_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_select(self, channel_set_ptr: c_void_p, 
                        select_type: c_uint, timeout: c_uint) -> 'J2534Err':
        raise NotImplementedError
    
    def pass_thru_write_msgs(self, channel_id: c_int, msg: c_void_p,
                            num_msgs: c_int, timeout: c_int) -> 'J2534Err':
        raise NotImplementedError


class IJ2534Extended(IJ2534):
    """Extended J2534 interface"""
    
    def get_config(self, channel_id: c_int, config: List['SConfig']) -> 'J2534Err':
        raise NotImplementedError
    
    def set_config(self, channel_id: c_int, config: List['SConfig']) -> 'J2534Err':
        raise NotImplementedError
    
    def sw_can_bus_speed(self, channel_id: c_int, option: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def read_battery_voltage(self, device_id: c_int, voltage: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def read_programming_voltage(self, device_id: c_int, voltage: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def five_baud_init(self, channel_id: c_int, target_address: c_ubyte,
                      keyword1: c_ubyte, keyword2: c_ubyte) -> 'J2534Err':
        raise NotImplementedError
    
    def fast_init(self, channel_id: c_int, tx_msg: 'PassThruMsg', 
                 rx_msg: 'PassThruMsg') -> 'J2534Err':
        raise NotImplementedError
    
    def clear_tx_buffer(self, channel_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def clear_rx_buffer(self, channel_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def clear_periodic_msgs(self, channel_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def clear_msg_filters(self, channel_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def clear_funct_msg_lookup_table(self, channel_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def add_to_funct_msg_lookup_table(self, channel_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def delete_from_funct_msg_lookup_table(self, channel_id: c_int) -> 'J2534Err':
        raise NotImplementedError
    
    def read_all_messages(self, channel_id: c_int, num_msgs: c_int, 
                         timeout: c_int, read_until_timeout: bool = True) -> tuple['J2534Err', List['PassThruMsg']]:
        raise NotImplementedError


class Ioctl(IntEnum):
    GET_CONFIG = 0x01
    SET_CONFIG = 0x02
    READ_VBATT = 0x03
    FIVE_BAUD_INIT = 0x04
    FAST_INIT = 0x05
    CLEAR_TX_BUFFER = 0x07
    CLEAR_RX_BUFFER = 0x08
    CLEAR_PERIODIC_MSGS = 0x09
    CLEAR_MSG_FILTERS = 0x0A
    CLEAR_FUNCT_MSG_LOOKUP_TABLE = 0x0B
    ADD_TO_FUNCT_MSG_LOOKUP_TABLE = 0x0C
    DELETE_FROM_FUNCT_MSG_LOOKUP_TABLE = 0x0D
    READ_PROG_VOLTAGE = 0x0E
    BUS_ON = 0x0F
    SW_CAN_HS = 0x8000  # Request swcan Highspeed
    SW_CAN_NS = 0x8001  # Request swcan low speed
    SET_POLL_RESPONSE = 0x8002  # aldl
    BECOME_MASTER = 0x8003  # aldl
    START_REPEAT_MESSAGE = 0x8004
    QUERY_REPEAT_MESSAGE = 0x8005
    STOP_REPEAT_MESSAGE = 0x8006
    GET_ConnectedDevice_CONFIG = 0x8007
    SET_ConnectedDevice_CONFIG = 0x8008
    PROTECT_J1939_ADDR = 0x8009
    REQUEST_CONNECTION = 0x800A
    TEARDOWN_CONNECTION = 0x800B
    GET_Device_INFO = 0x800C
    GET_PROTOCOL_INFO = 0x800D
    OBDX_AvailableDevices = 0x10000001


class GET_DEVICE_INFO_Defines(IntEnum):
    OBDX_UniqueSerial_Part1 = 0x10000001
    OBDX_UniqueSerial_Part2 = 0x10000002
    OBDX_UniqueSerial_Part3 = 0x10000003
    OBDX_UniqueSerial_Part4 = 0x10000004
    SERIAL_NUMBER = 0x00000001
    J1850PWM_SUPPORTED = 0x00000002
    J1850VPW_SUPPORTED = 0x00000003
    ISO9141_SUPPORTED = 0x00000004
    ISO14230_SUPPORTED = 0x00000005
    CAN_SUPPORTED = 0x00000006
    ISO15765_SUPPORTED = 0x00000007
    SCI_A_ENGINE_SUPPORTED = 0x00000008
    SCI_A_TRANS_SUPPORTED = 0x00000009
    SCI_B_ENGINE_SUPPORTED = 0x0000000A
    SCI_B_TRANS_SUPPORTED = 0x0000000B
    SW_ISO15765_SUPPORTED = 0x0000000C
    SW_CAN_SUPPORTED = 0x0000000D
    GM_UART_SUPPORTED = 0x0000000E
    UART_ECHO_BYTE_SUPPORTED = 0x0000000F
    HONDA_DIAGH_SUPPORTED = 0x00000010
    J1939_SUPPORTED = 0x00000011
    J1708_SUPPORTED = 0x00000012
    TP2_0_SUPPORTED = 0x00000013
    J2610_SUPPORTED = 0x00000014
    ANALOG_IN_SUPPORTED = 0x00000015
    MAX_NON_VOLATILE_STORAGE = 0x00000016
    SHORT_TO_GND_J1962 = 0x00000017
    PGM_VOLTAGE_J1962 = 0x00000018
    J1850PWM_PS_J1962 = 0x00000019
    J1850VPW_PS_J1962 = 0x0000001A
    ISO9141_PS_K_LINE_J1962 = 0x0000001B
    ISO9141_PS_L_LINE_J1962 = 0x0000001C
    ISO14230_PS_K_LINE_J1962 = 0x0000001D
    ISO14230_PS_L_LINE_J1962 = 0x0000001E
    CAN_PS_J1962 = 0x0000001F
    ISO15765_PS_J1962 = 0x00000020
    SW_CAN_PS_J1962 = 0x00000021
    SW_ISO15765_PS_J1962 = 0x00000022
    GM_UART_PS_J1962 = 0x00000023
    UART_ECHO_BYTE_PS_J1962 = 0x00000024
    HONDA_DIAGH_PS_J1962 = 0x00000025
    J1939_PS_J1962 = 0x00000026
    J1708_PS_J1962 = 0x00000027
    TP2_0_PS_J1962 = 0x00000028
    J2610_PS_J1962 = 0x00000029
    J1939_PS_J1939 = 0x0000002A
    J1708_PS_J1939 = 0x0000002B
    ISO9141_PS_K_LINE_J1939 = 0x0000002C
    ISO9141_PS_L_LINE_J1939 = 0x0000002D
    ISO14230_PS_K_LINE_J1939 = 0x0000002E
    ISO14230_PS_L_LINE_J1939 = 0x0000002F
    J1708_PS_J1708 = 0x00000030
    FT_CAN_SUPPORTED = 0x00000031
    FT_ISO15765_SUPPORTED = 0x00000032
    FT_CAN_PS_J1962 = 0x00000033
    FT_ISO15765_PS_J1962 = 0x00000034
    J1850PWM_SIMULTANEOUS = 0x00000035
    J1850VPW_SIMULTANEOUS = 0x00000036
    ISO9141_SIMULTANEOUS = 0x00000037
    ISO14230_SIMULTANEOUS = 0x00000038
    CAN_SIMULTANEOUS = 0x00000039
    ISO15765_SIMULTANEOUS = 0x0000003A
    SCI_A_ENGINE_SIMULTANEOUS = 0x0000003B
    SCI_A_TRANS_SIMULTANEOUS = 0x0000003C
    SCI_B_ENGINE_SIMULTANEOUS = 0x0000003D
    SCI_B_TRANS_SIMULTANEOUS = 0x0000003E
    SW_ISO15765_SIMULTANEOUS = 0x0000003F
    SW_CAN_SIMULTANEOUS = 0x00000040
    GM_UART_SIMULTANEOUS = 0x00000041
    UART_ECHO_BYTE_SIMULTANEOUS = 0x00000042
    HONDA_DIAGH_SIMULTANEOUS = 0x00000043
    J1939_SIMULTANEOUS = 0x00000044
    J1708_SIMULTANEOUS = 0x00000045
    TP2_0_SIMULTANEOUS = 0x00000046
    J2610_SIMULTANEOUS = 0x00000047
    ANALOG_IN_SIMULTANEOUS = 0x00000048
    PART_NUMBER = 0x00000049
    FT_CAN_SIMULTANEOUS = 0x0000004A
    FT_ISO15765_SIMULTANEOUS = 0x0000004B


class RxStatus(IntFlag):
    NONE = 0x00000000
    TX_MSG_TYPE = 0x00000001
    START_OF_MESSAGE = 0x00000002
    RX_BREAK = 0x00000004
    TX_INDICATION_SUCCESS = 0x00000008
    ISO15765_PADDING_ERROR = 0x00000010
    ERROR_INDICATION = 0x20
    BUFFER_OVERFLOW = 0x40
    ISO15765_ADDR_TYPE = 0x00000080
    CAN_29BIT_ID = 0x00000100
    TX_FAILED = 0x200
    SW_CAN_HV_TX = 0x00000400
    SW_CAN_NS_RX = 0x00040000
    SW_CAN_HS_RX = 0x00020000
    SW_CAN_HV_RX = 0x00010000


class ConnectFlag(IntFlag):
    NONE = 0x0000
    ISO9141_K_LINE_ONLY = 0x1000
    CAN_ID_BOTH = 0x0800
    ISO9141_NO_CHECKSUM = 0x0200
    CAN_29BIT_ID = 0x0100
    FULL_DUPLEX = 0x1


class TxFlag(IntFlag):
    NONE = 0x00000000
    SCI_TX_VOLTAGE = 0x00800000
    SCI_MODE = 0x00400000
    WAIT_P3_MIN_ONLY = 0x00000200
    CAN_29BIT_ID = 0x00000100
    ISO15765_ADDR_TYPE = 0x00000080
    ISO15765_FRAME_PAD = 0x00000040
    SW_CAN_HV_TX = 0x00000400


class ProtocolID(IntEnum):
    J1850VPW = 0x01
    J1850PWM = 0x02
    ISO9141 = 0x03
    ISO14230 = 0x04
    CAN = 0x05
    ISO15765 = 0x06
    SCI_A_ENGINE = 0x07
    SCI_A_TRANS = 0x08
    SCI_B_ENGINE = 0x09
    SCI_B_TRANS = 0x0A
    ISO15765_LOGICAL = 0x200
    # J2534-2 protocols
    J1850VPW_PS = 0x8000
    J1850PWM_PS = 0x8001
    ISO9141_PS = 0x8002
    ISO14230_PS = 0x8003
    CAN_PS = 0x8004
    ISO15765_PS = 0x8005
    J2610_PS = 0x8006
    SW_ISO15765_PS = 0x8007
    SW_CAN_PS = 0x8008
    GM_UART_PS = 0x8009
    UART_ECHO_BYTE_PS = 0x800A
    HONDA_DIAGH_PS = 0x800B
    J1939_PS = 0x800C
    J1708_PS = 0x800D
    TP2_0_PS = 0x800E
    FT_CAN_PS = 0x800F
    FT_ISO15765_PS = 0x8010


class BaudRate(IntEnum):
    ISO9141_10400 = 10400
    ISO9141_10000 = 10000
    
    ISO14230_10400 = 10400
    ISO14230_10000 = 10000
    
    J1850PWM_41600 = 41600
    J1850PWM_83300 = 83300
    
    J1850VPW_10400 = 10400
    J1850VPW_41600 = 41600
    
    CAN_125000 = 125000
    CAN_250000 = 250000
    CAN_500000 = 500000
    CAN_33333 = 33333
    CAN_83333 = 83333
    
    ISO15765_125000 = 125000
    ISO15765_250000 = 250000
    ISO15765_500000 = 500000
    
    GMUART_8192 = 8192
    GMUART_160 = 160


class PinNumber(IntEnum):
    AUX = 0
    PIN_1 = 1
    PIN_3 = 3
    PIN_6 = 6
    PIN_9 = 9
    PIN_11 = 11
    PIN_12 = 12
    PIN_13 = 13
    PIN_14 = 14
    PIN_15 = 15


class PinVoltage(IntEnum):
    FEPS_VOLTAGE = 18000
    SHORT_TO_GROUND = 0xFFFFFFFE
    VOLTAGE_OFF = 0xFFFFFFFF


class FilterType(IntEnum):
    PASS_FILTER = 0x01
    BLOCK_FILTER = 0x02
    FLOW_CONTROL_FILTER = 0x03


class J2534Err(IntEnum):
    STATUS_NOERROR = 0x00
    ERR_NOT_SUPPORTED = 0x01
    ERR_INVALID_CHANNEL_ID = 0x02
    ERR_INVALID_PROTOCOL_ID = 0x03
    ERR_NULL_PARAMETER = 0x04
    ERR_INVALID_FLAGS = 0x06
    ERR_FAILED = 0x07
    ERR_ConnectedDevice_NOT_CONNECTED = 0x08
    ERR_TIMEOUT = 0x09
    ERR_INVALID_MSG = 0x0A
    ERR_INVALID_TIME_INTERVAL = 0x0B
    ERR_EXCEEDED_LIMIT = 0x0C
    ERR_INVALID_MSG_ID = 0x0D
    ERR_ConnectedDevice_IN_USE = 0x0E
    ERR_INVALID_IOCTL_ID = 0x0F
    ERR_BUFFER_EMPTY = 0x10
    ERR_BUFFER_FULL = 0x11
    ERR_BUFFER_OVERFLOW = 0x12
    ERR_PIN_INVALID = 0x13
    ERR_CHANNEL_IN_USE = 0x14
    ERR_MSG_PROTOCOL_ID = 0x15
    ERR_INVALID_FILTER_ID = 0x16
    ERR_NO_FLOW_CONTROL = 0x17
    ERR_NOT_UNIQUE = 0x18
    ERR_INVALID_BAUDRATE = 0x19
    ERR_INVALID_ConnectedDevice_ID = 0x1A
    ERR_ConnectedDevice_NOT_OPEN = 0X1B
    ERR_NULL_REQUIRED = 0X1C
    ERR_FILTER_TYPE_NOT_SUPPORTED = 0X1D
    ERR_IOCTL_PARAM_ID_NOT_SUPPORTED = 0X1E
    ERR_VOLTAGE_IN_USE = 0X1F
    ERR_PIN_IN_USE = 0X20
    ERR_INIT_FAILED = 0X21
    ERR_OPEN_FAILED = 0X22
    ERR_BUFFER_TOO_SMALL = 0X23
    ERR_LOG_CHAN_NOT_ALLOWED = 0X24
    ERR_SELECT_TYPE_NOT_SUPPORTED = 0X25
    ERR_CONCURRENT_API_CALL = 0X26
    ERR_OEM_VOLTAGE_TOO_HIGH = 0x77
    ERR_OEM_VOLTAGE_TOO_LOW = 0x78
    ERR_ACCESS_VIOLATION = 0x1000
    ERR_DLL_NOT_LOADED = 0x1001
    ERR_RESOURCE_IN_USE = 0x1002
    ERR_OUT_OF_MEMORY = 0x1999
    ERR_ALDL_HEARTBEAT_NOT_FOUND = 0x5000
    ERR_NO_RESPONSE_FROM_MODULE = 0x5001


class J2534Device:
    def __init__(self):
        self.vendor = ""
        self.name = ""
        self.function_library = ""
        self.config_application = ""
        self.can = 0
        self.iso14230 = 0
        self.iso15765 = 0
        self.iso9141 = 0
        self.j1850pwm = 0
        self.j1850vpw = 0
        self.sci_a_engine = 0
        self.sci_a_trans = 0
        self.sci_b_engine = 0
        self.sci_b_trans = 0
        self.can_ps = 0
        self.ft_can_ps = 0
        self.ft_iso15765_ps = 0
        self.gm_uart_ps = 0
        self.iso14230_ps = 0
        self.iso15765_ps = 0
        self.iso9141_ps = 0
        self.sw_can_ps = 0
        self.sw_iso15765_ps = 0
        self.j1850vpw_ps = 0
    
    def __str__(self):
        return self.name


class NativeMethods:
    """Platform-specific library loading methods"""
    
    @staticmethod
    def load_library(dll_path: str):
        """Load library using ctypes"""
        if sys.platform == 'win32':
            return ctypes.WinDLL(dll_path)
        else:
            return ctypes.CDLL(dll_path)
    
    @staticmethod
    def get_proc_address(dll, proc_name: str):
        """Get function pointer from DLL"""
        try:
            return getattr(dll, proc_name)
        except AttributeError:
            return None
    
    @staticmethod
    def free_library(dll):
        """Free the library"""
        if dll is not None:
            # Python's ctypes handles cleanup automatically
            del dll
        return True


class J2534DllWrapper:
    def __init__(self):
        self.m_p_dll = None
        
        # Function pointers
        self.open = None
        self.close = None
        self.scan_for_devices = None
        self.get_next_device = None
        self.connect = None
        self.disconnect = None
        self.read_msgs = None
        self.write_msgs = None
        self.write_queue_msgs = None
        self.connect_logical = None
        self.disconnect_logical = None
        self.select_channel_to_check = None
        self.start_periodic_msg = None
        self.stop_periodic_msg = None
        self.start_msg_filter = None
        self.start_pass_block_msg_filter = None
        self.stop_msg_filter = None
        self.set_programming_voltage = None
        self.read_version = None
        self.get_last_error = None
        self.ioctl = None
    
    def load_j2534_library(self, path: str) -> bool:
        try:
            self.m_p_dll = NativeMethods.load_library(path)
            
            if self.m_p_dll is None:
                return False
            
            # Load PassThruOpen
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruOpen")
            if func is not None:
                func.argtypes = [c_void_p, POINTER(c_uint)]
                func.restype = c_int
                self.open = func
            else:
                return False
            
            # Load PassThruClose
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruClose")
            if func is not None:
                func.argtypes = [c_uint]
                func.restype = c_int
                self.close = func
            else:
                return False
            
            # Load PassThruConnect
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruConnect")
            if func is not None:
                func.argtypes = [c_uint, c_uint, c_uint, c_uint, POINTER(c_uint)]
                func.restype = c_int
                self.connect = func
            else:
                return False
            
            # Load PassThruDisconnect
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruDisconnect")
            if func is not None:
                func.argtypes = [c_int]
                func.restype = c_int
                self.disconnect = func
            else:
                return False
            
            # Load PassThruReadMsgs
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruReadMsgs")
            if func is not None:
                func.argtypes = [c_int, c_void_p, POINTER(c_int), c_int]
                func.restype = c_int
                self.read_msgs = func
            else:
                return False
            
            # Load PassThruWriteMsgs
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruWriteMsgs")
            if func is not None:
                func.argtypes = [c_int, c_void_p, POINTER(c_int), c_int]
                func.restype = c_int
                self.write_msgs = func
            else:
                return False
            
            # Load PassThruStartPeriodicMsg
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruStartPeriodicMsg")
            if func is not None:
                func.argtypes = [c_int, c_void_p, POINTER(c_int), c_int]
                func.restype = c_int
                self.start_periodic_msg = func
            else:
                return False
            
            # Load PassThruStopPeriodicMsg
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruStopPeriodicMsg")
            if func is not None:
                func.argtypes = [c_int, c_int]
                func.restype = c_int
                self.stop_periodic_msg = func
            else:
                return False
            
            # Load PassThruStartMsgFilter
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruStartMsgFilter")
            if func is not None:
                func.argtypes = [c_int, c_int, c_void_p, c_void_p, c_void_p, POINTER(c_int)]
                func.restype = c_int
                self.start_msg_filter = func
                self.start_pass_block_msg_filter = func
            else:
                return False
            
            # Load PassThruStopMsgFilter
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruStopMsgFilter")
            if func is not None:
                func.argtypes = [c_int, c_int]
                func.restype = c_int
                self.stop_msg_filter = func
            else:
                return False
            
            # Load PassThruSetProgrammingVoltage
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruSetProgrammingVoltage")
            if func is not None:
                func.argtypes = [c_int, c_uint, c_uint]
                func.restype = c_int
                self.set_programming_voltage = func
            else:
                return False
            
            # Load PassThruReadVersion
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruReadVersion")
            if func is not None:
                func.argtypes = [c_int, c_void_p, c_void_p, c_void_p]
                func.restype = c_int
                self.read_version = func
            else:
                return False
            
            # Load PassThruGetLastError
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruGetLastError")
            if func is not None:
                func.argtypes = [c_void_p]
                func.restype = c_int
                self.get_last_error = func
            else:
                return False
            
            # Load PassThruIoctl
            func = NativeMethods.get_proc_address(self.m_p_dll, "PassThruIoctl")
            if func is not None:
                func.argtypes = [c_int, c_int, c_void_p, c_void_p]
                func.restype = c_int
                self.ioctl = func
            else:
                return False
            
            return True
            
        except Exception as e:
            return False
    
    def free_library(self) -> bool:
        if self.m_p_dll is not None:
            NativeMethods.free_library(self.m_p_dll)
        return True


class J2534Functions(IJ2534):
    # --- Compatibility aliases for PascalCase callers (e.g., J2534_Port) ---

    # DLL management
    def LoadLibrary(self, device):                     # device is your J2534Device
        return self.load_library(device)

    def FreeLibrary(self):
        return self.free_library()

    # Core J2534 API
    def PassThruOpen(self, name, device_id):          # (ctypes ptr or int), device_id: ctypes byref
        return self.pass_thru_open(name, device_id)

    def PassThruClose(self, device_id):
        return self.pass_thru_close(device_id)

    def PassThruConnect(self, device_id, protocol_id, flags, baud_rate, channel_id):
        return self.pass_thru_connect(device_id, protocol_id, flags, baud_rate, channel_id)

    def PassThruDisconnect(self, channel_id):
        return self.pass_thru_disconnect(channel_id)

    def PassThruReadMsgs(self, channel_id, msgs, num_msgs, timeout):
        return self.pass_thru_read_msgs(channel_id, msgs, num_msgs, timeout)

    def PassThruWriteMsgs(self, channel_id, msgs, num_msgs, timeout):
        return self.pass_thru_write_msgs(channel_id, msgs, num_msgs, timeout)

    def PassThruStartPeriodicMsg(self, channel_id, msg, msg_id, time_interval):
        return self.pass_thru_start_periodic_msg(channel_id, msg, msg_id, time_interval)

    def PassThruStopPeriodicMsg(self, channel_id, msg_id):
        return self.pass_thru_stop_periodic_msg(channel_id, msg_id)

    def PassThruStartMsgFilter(self, channel_id, filter_type, mask_msg, pattern_msg, flow_control_msg, filter_id):
        return self.pass_thru_start_msg_filter(channel_id, filter_type, mask_msg, pattern_msg, flow_control_msg, filter_id)

    def PassThruStopMsgFilter(self, channel_id, filter_id):
        return self.pass_thru_stop_msg_filter(channel_id, filter_id)

    def PassThruSetProgrammingVoltage(self, device_id, pin_number, voltage):
        return self.pass_thru_set_programming_voltage(device_id, pin_number, voltage)

    def PassThruReadVersion(self, device_id, firmware_version, dll_version, api_version):
        return self.pass_thru_read_version(device_id, firmware_version, dll_version, api_version)

    def PassThruGetLastError(self, error_description):
        return self.pass_thru_get_last_error(error_description)

    def PassThruIoctl(self, channel_id, ioctl_id, input_ptr, output_ptr):
        return self.pass_thru_ioctl(channel_id, ioctl_id, input_ptr, output_ptr)

    # Extended helpers (keep parity with your snake_case helpers)
    def GetConfig(self, channel_id, config):
        return self.get_config(channel_id, config)

    def SetConfig(self, channel_id, config):
        return self.set_config(channel_id, config)

    def ReadVBatt(self, device_id, voltage):
        return self.read_battery_voltage(device_id, voltage)

    def ReadProgVoltage(self, device_id, voltage):
        return self.read_programming_voltage(device_id, voltage)

    def FiveBaudInit(self, channel_id, target_address, keyword1, keyword2):
        return self.five_baud_init(channel_id, target_address, keyword1, keyword2)

    def FastInit(self, channel_id, tx_msg, rx_msg):
        return self.fast_init(channel_id, tx_msg, rx_msg)

    def ClearTXBuffer(self, channel_id):
        return self.clear_tx_buffer(channel_id)

    def ClearRXBuffer(self, channel_id):
        return self.clear_rx_buffer(channel_id)

    def ClearPeriodicMsgs(self, channel_id):
        return self.clear_periodic_msgs(channel_id)

    def ClearMsgFilters(self, channel_id):
        return self.clear_msg_filters(channel_id)

    
    def __init__(self):
        self._connected_device = None
        self._j2534_dll_wrapper = None
        self._is_dll_loaded = False
    
    def __str__(self):
        return "Copyright Envyous Customs - J2534 API DLL - For Authorised Applications Only."
    
    @property
    def is_dll_loaded(self) -> bool:
        return self._is_dll_loaded
    
    @property
    def device_name(self) -> str:
        if self._connected_device:
            return self._connected_device.name
        return ""
    
    def load_library(self, device: J2534Device) -> bool:
        try:
            self._connected_device = device
            self._j2534_dll_wrapper = J2534DllWrapper()
            self._is_dll_loaded = self._j2534_dll_wrapper.load_j2534_library(
                self._connected_device.function_library
            )
            return self._is_dll_loaded
        except Exception:
            self._is_dll_loaded = False
            return self._is_dll_loaded
    
    def free_library(self) -> bool:
        self._is_dll_loaded = False
        if self._j2534_dll_wrapper is not None:
            return self._j2534_dll_wrapper.free_library()
        return True
    
    def pass_thru_open(self, name: c_void_p, device_id: c_uint) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            result = J2534Err(self._j2534_dll_wrapper.open(name, byref(device_id)))
            return result
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_close(self, device_id: c_uint) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.close(device_id))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_scan_for_devices(self, device_count: c_int) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.scan_for_devices(byref(device_count)))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_get_next_device(self, device: 'SDEVICE') -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.get_next_device(byref(device)))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_queue_msgs(self, channel_id: c_int, msgs: c_void_p, num_msgs: c_int) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.write_queue_msgs(channel_id, msgs, byref(num_msgs)))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_logical_connect(self, physical_channel_id: c_int, protocol_id: ProtocolID,
                                  flags: ConnectFlag, channel_descriptor: c_void_p,
                                  logical_channel_id: c_int) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.connect_logical(
                physical_channel_id, protocol_id, flags, byref(channel_descriptor), byref(logical_channel_id)
            ))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_logical_disconnect(self, logical_channel_id: c_int) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.disconnect_logical(logical_channel_id))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_select(self, channel_set_ptr: c_void_p, select_type: c_uint, timeout: c_uint) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.select_channel_to_check(
                byref(channel_set_ptr), select_type, timeout
            ))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_connect(self, device_id: c_uint, protocol_id: ProtocolID,
                         flags: ConnectFlag, baud_rate: BaudRate, channel_id: c_uint) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.connect(
                device_id, protocol_id, flags, baud_rate, byref(channel_id)
            ))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_disconnect(self, channel_id: c_int) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.disconnect(channel_id))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_read_msgs(self, channel_id: c_int, msgs: c_void_p, num_msgs: c_int, timeout: c_int) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.read_msgs(channel_id, msgs, byref(num_msgs), timeout))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_write_msgs(self, channel_id: c_int, msgs: c_void_p, num_msgs: c_int, timeout: c_int) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.write_msgs(channel_id, msgs, byref(num_msgs), timeout))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_start_periodic_msg(self, channel_id: c_int, msg: c_void_p, msg_id: c_int, time_interval: c_int) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.start_periodic_msg(channel_id, msg, byref(msg_id), time_interval))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_stop_periodic_msg(self, channel_id: c_int, msg_id: c_int) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.stop_periodic_msg(channel_id, msg_id))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_start_msg_filter(self, channel_id: c_int, filter_type: FilterType,
                                   mask_msg: c_void_p, pattern_msg: c_void_p,
                                   flow_control_msg: c_void_p, filter_id: c_int) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.start_msg_filter(
                channel_id, int(filter_type), mask_msg, pattern_msg, flow_control_msg, byref(filter_id)
            ))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_stop_msg_filter(self, channel_id: c_int, filter_id: c_int) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.stop_msg_filter(channel_id, filter_id))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_set_programming_voltage(self, device_id: c_int, pin_number: PinNumber, voltage: c_uint) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.set_programming_voltage(device_id, int(pin_number), voltage))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_read_version(self, device_id: c_int, firmware_version: c_void_p,
                              dll_version: c_void_p, api_version: c_void_p) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.read_version(
                device_id, firmware_version, dll_version, api_version
            ))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_get_last_error(self, error_description: c_void_p) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.get_last_error(error_description))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION
    
    def pass_thru_ioctl(self, channel_id: c_int, ioctl_id: c_int, input_ptr: c_void_p, output_ptr: c_void_p) -> J2534Err:
        try:
            if not self.is_dll_loaded:
                return J2534Err.ERR_DLL_NOT_LOADED
            return J2534Err(self._j2534_dll_wrapper.ioctl(channel_id, ioctl_id, input_ptr, output_ptr))
        except Exception:
            return J2534Err.ERR_ACCESS_VIOLATION


class J2534FunctionsExtended(J2534Functions, IJ2534Extended):
        # --- Compatibility aliases for PascalCase callers (e.g., J2534_Port) ---

    # DLL management
    def LoadLibrary(self, device):                     # device is your J2534Device
        return self.load_library(device)

    def FreeLibrary(self):
        return self.free_library()

    # Core J2534 API
    def PassThruOpen(self, name, device_id):          # (ctypes ptr or int), device_id: ctypes byref
        return self.pass_thru_open(name, device_id)

    def PassThruClose(self, device_id):
        return self.pass_thru_close(device_id)

    def PassThruConnect(self, device_id, protocol_id, flags, baud_rate, channel_id):
        return self.pass_thru_connect(device_id, protocol_id, flags, baud_rate, channel_id)

    def PassThruDisconnect(self, channel_id):
        return self.pass_thru_disconnect(channel_id)

    def PassThruReadMsgs(self, channel_id, msgs, num_msgs, timeout):
        return self.pass_thru_read_msgs(channel_id, msgs, num_msgs, timeout)

    def PassThruWriteMsgs(self, channel_id, msgs, num_msgs, timeout):
        return self.pass_thru_write_msgs(channel_id, msgs, num_msgs, timeout)

    def PassThruStartPeriodicMsg(self, channel_id, msg, msg_id, time_interval):
        return self.pass_thru_start_periodic_msg(channel_id, msg, msg_id, time_interval)

    def PassThruStopPeriodicMsg(self, channel_id, msg_id):
        return self.pass_thru_stop_periodic_msg(channel_id, msg_id)

    def PassThruStartMsgFilter(self, channel_id, filter_type, mask_msg, pattern_msg, flow_control_msg, filter_id):
        return self.pass_thru_start_msg_filter(channel_id, filter_type, mask_msg, pattern_msg, flow_control_msg, filter_id)

    def PassThruStopMsgFilter(self, channel_id, filter_id):
        return self.pass_thru_stop_msg_filter(channel_id, filter_id)

    def PassThruSetProgrammingVoltage(self, device_id, pin_number, voltage):
        return self.pass_thru_set_programming_voltage(device_id, pin_number, voltage)

    def PassThruReadVersion(self, device_id, firmware_version, dll_version, api_version):
        return self.pass_thru_read_version(device_id, firmware_version, dll_version, api_version)

    def PassThruGetLastError(self, error_description):
        return self.pass_thru_get_last_error(error_description)

    def PassThruIoctl(self, channel_id, ioctl_id, input_ptr, output_ptr):
        return self.pass_thru_ioctl(channel_id, ioctl_id, input_ptr, output_ptr)

    # Extended helpers (keep parity with your snake_case helpers)
    def GetConfig(self, channel_id, config):
        return self.get_config(channel_id, config)

    def SetConfig(self, channel_id, config):
        return self.set_config(channel_id, config)

    def ReadVBatt(self, device_id, voltage):
        return self.read_battery_voltage(device_id, voltage)

    def ReadProgVoltage(self, device_id, voltage):
        return self.read_programming_voltage(device_id, voltage)

    def FiveBaudInit(self, channel_id, target_address, keyword1, keyword2):
        return self.five_baud_init(channel_id, target_address, keyword1, keyword2)

    def FastInit(self, channel_id, tx_msg, rx_msg):
        return self.fast_init(channel_id, tx_msg, rx_msg)

    def ClearTXBuffer(self, channel_id):
        return self.clear_tx_buffer(channel_id)

    def ClearRXBuffer(self, channel_id):
        return self.clear_rx_buffer(channel_id)

    def ClearPeriodicMsgs(self, channel_id):
        return self.clear_periodic_msgs(channel_id)

    def ClearMsgFilters(self, channel_id):
        return self.clear_msg_filters(channel_id)

    def get_config(self, channel_id: c_int, config: List['SConfig']) -> J2534Err:
        try:
            s_config_list = SConfigList()
            s_config_list.count = len(config)
            s_config_list.list_ptr = (SConfig * len(config))()
            
            for i, cfg in enumerate(config):
                s_config_list.list_ptr[i] = cfg
            
            output = c_void_p()
            input_ptr = pointer(s_config_list)
            
            err = J2534Err(self._j2534_dll_wrapper.ioctl(
                channel_id, int(Ioctl.GET_CONFIG), input_ptr, output
            ))
            
            config.clear()
            for i in range(s_config_list.count):
                config.append(s_config_list.list_ptr[i])
            
            return err
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def set_config(self, channel_id: c_int, config: List['SConfig']) -> J2534Err:
        try:
            s_config_list = SConfigList()
            s_config_list.count = len(config)
            s_config_list.list_ptr = (SConfig * len(config))()
            
            for i, cfg in enumerate(config):
                s_config_list.list_ptr[i] = cfg
            
            output = c_void_p()
            input_ptr = pointer(s_config_list)
            
            err = J2534Err(self._j2534_dll_wrapper.ioctl(
                channel_id, int(Ioctl.SET_CONFIG), input_ptr, output
            ))
            
            return err
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def sw_can_bus_speed(self, channel_id: c_int, option: c_int) -> J2534Err:
        try:
            input_ptr = c_void_p()
            output = c_void_p()
            
            if option == 0:
                return J2534Err(self._j2534_dll_wrapper.ioctl(
                    channel_id, int(Ioctl.SW_CAN_HS), input_ptr, output
                ))
            else:
                return J2534Err(self._j2534_dll_wrapper.ioctl(
                    channel_id, int(Ioctl.SW_CAN_NS), input_ptr, output
                ))
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def read_battery_voltage(self, device_id: c_int, voltage: c_int) -> J2534Err:
        try:
            input_ptr = c_void_p()
            output = c_int()
            
            return_value = J2534Err(self._j2534_dll_wrapper.ioctl(
                device_id, int(Ioctl.READ_VBATT), input_ptr, byref(output)
            ))
            
            if return_value == J2534Err.STATUS_NOERROR:
                voltage.value = output.value
            
            return return_value
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def clear_tx_buffer(self, channel_id: c_int) -> J2534Err:
        try:
            input_ptr = c_void_p()
            output = c_void_p()
            
            return J2534Err(self._j2534_dll_wrapper.ioctl(
                channel_id, int(Ioctl.CLEAR_TX_BUFFER), input_ptr, output
            ))
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def clear_rx_buffer(self, channel_id: c_int) -> J2534Err:
        try:
            input_ptr = c_void_p()
            output = c_void_p()
            
            return J2534Err(self._j2534_dll_wrapper.ioctl(
                channel_id, int(Ioctl.CLEAR_RX_BUFFER), input_ptr, output
            ))
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def clear_periodic_msgs(self, channel_id: c_int) -> J2534Err:
        try:
            input_ptr = c_void_p()
            output = c_void_p()
            
            return J2534Err(self._j2534_dll_wrapper.ioctl(
                channel_id, int(Ioctl.CLEAR_PERIODIC_MSGS), input_ptr, output
            ))
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def clear_msg_filters(self, channel_id: c_int) -> J2534Err:
        try:
            input_ptr = c_void_p()
            output = c_void_p()
            
            return J2534Err(self._j2534_dll_wrapper.ioctl(
                channel_id, int(Ioctl.CLEAR_MSG_FILTERS), input_ptr, output
            ))
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def clear_funct_msg_lookup_table(self, channel_id: c_int) -> J2534Err:
        try:
            input_ptr = c_void_p()
            output = c_void_p()
            
            return J2534Err(self._j2534_dll_wrapper.ioctl(
                channel_id, int(Ioctl.CLEAR_FUNCT_MSG_LOOKUP_TABLE), input_ptr, output
            ))
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def add_to_funct_msg_lookup_table(self, channel_id: c_int) -> J2534Err:
        try:
            input_ptr = c_void_p()
            output = c_void_p()
            # TODO: fix this
            return J2534Err(self._j2534_dll_wrapper.ioctl(
                channel_id, int(Ioctl.ADD_TO_FUNCT_MSG_LOOKUP_TABLE), input_ptr, output
            ))
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def delete_from_funct_msg_lookup_table(self, channel_id: c_int) -> J2534Err:
        try:
            input_ptr = c_void_p()
            output = c_void_p()
            # TODO: fix this
            return J2534Err(self._j2534_dll_wrapper.ioctl(
                channel_id, int(Ioctl.DELETE_FROM_FUNCT_MSG_LOOKUP_TABLE), input_ptr, output
            ))
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def read_all_messages(self, channel_id: c_int, num_msgs: c_int, timeout: c_int,
                         read_until_timeout: bool = True) -> tuple[J2534Err, List['PassThruMsg']]:
        """Poll for messages until we get a timeout"""
        messages = []
        try:
            rx_msgs_array = (PassThruMsg * num_msgs.value)()
            rx_msgs = cast(rx_msgs_array, c_void_p)
            m_status = J2534Err.STATUS_NOERROR
            m_status2 = J2534Err.STATUS_NOERROR
            
            # Read the first block of messages
            num_msgs_ref = c_int(num_msgs.value)
            m_status = self.pass_thru_read_msgs(channel_id, rx_msgs, num_msgs_ref, timeout)
            
            if m_status == J2534Err.STATUS_NOERROR:
                for i in range(num_msgs_ref.value):
                    messages.append(rx_msgs_array[i])
                
                # If we are only reading this block then return now
                if not read_until_timeout:
                    return (m_status, messages)
            else:
                for i in range(num_msgs_ref.value):
                    messages.append(rx_msgs_array[i])
                # If we failed on the first read give up now
                return (m_status, messages)
            
            # We successfully read one block, now keep going
            while m_status2 == J2534Err.STATUS_NOERROR:
                num_msgs_ref = c_int(num_msgs.value)
                m_status2 = self.pass_thru_read_msgs(channel_id, rx_msgs, num_msgs_ref, timeout)
                
                if m_status2 == J2534Err.STATUS_NOERROR:
                    for i in range(num_msgs_ref.value):
                        messages.append(rx_msgs_array[i])
                else:
                    break
            
            return (J2534Err.STATUS_NOERROR, messages)
            
        except MemoryError:
            return (J2534Err.ERR_OUT_OF_MEMORY, messages)


class J2534Exception(Exception):
    def __init__(self, error: J2534Err):
        self._error = error
        super().__init__(str(error))
    
    @property
    def error(self) -> J2534Err:
        return self._error


class OBDX_DeviceDetails(Structure):
    _fields_ = [
        ("DeviceName", c_void_p),
        ("UniqueSerial", c_void_p),
        ("HardwareVersion", c_void_p),
        ("FirmwareVersion", c_void_p),
        ("ComportNumber", c_uint),
    ]
    
    def set_device_name(self, val: str):
        self.DeviceName = cast(create_string_buffer(val.encode('ascii'), 80), c_void_p)
    
    def get_device_name(self) -> str:
        if self.DeviceName:
            return cast(self.DeviceName, c_char_p).value.decode('ascii')
        return ""
    
    def set_unique_serial(self, val: str):
        self.UniqueSerial = cast(create_string_buffer(val.encode('ascii'), 80), c_void_p)
    
    def get_unique_serial(self) -> str:
        if self.UniqueSerial:
            return cast(self.UniqueSerial, c_char_p).value.decode('ascii')
        return ""
    
    def set_hardware_version(self, val: str):
        self.HardwareVersion = cast(create_string_buffer(val.encode('ascii'), 80), c_void_p)
    
    def get_hardware_version(self) -> str:
        if self.HardwareVersion:
            return cast(self.HardwareVersion, c_char_p).value.decode('ascii')
        return ""
    
    def set_firmware_version(self, val: str):
        self.FirmwareVersion = cast(create_string_buffer(val.encode('ascii'), 80), c_void_p)
    
    def get_firmware_version(self) -> str:
        if self.FirmwareVersion:
            return cast(self.FirmwareVersion, c_char_p).value.decode('ascii')
        return ""


class OBDX_DeviceDetailsList(Structure):
    _fields_ = [
        ("Count", c_int),
        ("ListPtr", c_void_p),
    ]
    
    def get_list(self) -> List[OBDX_DeviceDetails]:
        if not self.ListPtr:
            return []
        array_type = OBDX_DeviceDetails * self.Count
        array = cast(self.ListPtr, POINTER(array_type)).contents
        return [array[i] for i in range(self.Count)]


class PassThruMsg(Structure):
    _fields_ = [
        ("ProtocolID", c_uint),
        ("RxStatus", c_uint),
        ("TxFlags", c_uint),
        ("Timestamp", c_uint),
        ("DataSize", c_uint),
        ("ExtraDataIndex", c_uint),
        ("Data", c_ubyte * 4128),
    ]
    
    def __init__(self, protocol_id: ProtocolID = None, tx_flag: TxFlag = None, byte_array: bytes = None):
        super().__init__()
        if protocol_id is not None:
            self.ProtocolID = protocol_id
        if tx_flag is not None:
            self.TxFlags = tx_flag
        if byte_array is not None:
            self.set_bytes(byte_array)
    
    def set_bytes(self, byte_array: bytes):
        self.DataSize = len(byte_array)
        for i in range(len(byte_array)):
            self.Data[i] = byte_array[i]
    
    def get_bytes(self) -> bytes:
        return bytes(self.Data[:self.DataSize])
    
    def to_string(self, tab: str = "    ") -> str:
        return (
            f"{tab}Protocol: {ProtocolID(self.ProtocolID).name}\n"
            f"{tab}RxStatus: {RxStatus(self.RxStatus).name}\n"
            f"{tab}Timestamp: {self.Timestamp}\n"
            f"{tab}ExtraDataIndex: {self.ExtraDataIndex}\n"
            f"{tab}Data: {self.get_bytes().hex(' ').upper()}"
        )
    
    def __str__(self):
        return self.to_string()


class SByteArray(Structure):
    _fields_ = [
        ("NumOfBytes", c_int),
        ("BytePtr", c_void_p),
    ]
    
    def __str__(self):
        if not self.BytePtr or self.NumOfBytes <= 0:
            return ""
        byte_array = cast(self.BytePtr, POINTER(c_ubyte * self.NumOfBytes)).contents
        return ' '.join(f'{byte_array[i]:02X}' for i in range(self.NumOfBytes))


class SConfig(Structure):
    _fields_ = [
        ("Parameter", c_uint),
        ("Value", c_uint16),
    ]


class SConfigList(Structure):
    _fields_ = [
        ("Count", c_int),
        ("ListPtr", c_void_p),
    ]
    
    def get_list(self) -> List[SConfig]:
        if not self.ListPtr:
            return []
        array_type = SConfig * self.Count
        array = cast(self.ListPtr, POINTER(array_type)).contents
        return [array[i] for i in range(self.Count)]


class SParam(Structure):
    _fields_ = [
        ("Parameter", c_uint),  # Name of parameter
        ("Value", c_uint),  # value of parameter
        ("Supported", c_uint),  # support for parameter
    ]


class SParamList(Structure):
    _fields_ = [
        ("Count", c_int),
        ("ListPtr", c_void_p),
    ]
    
    def get_list(self) -> List[SParam]:
        if not self.ListPtr:
            return []
        array_type = SParam * self.Count
        array = cast(self.ListPtr, POINTER(array_type)).contents
        return [array[i] for i in range(self.Count)]


class SDEVICE(Structure):
    _fields_ = [
        ("DeviceName", c_char * 80),
        ("DeviceAvailable", c_uint),
        ("DeviceDLLFWStatus", c_uint),
        ("DeviceConnectMedia", c_uint),
        ("DeviceConnectSpeed", c_uint),
        ("DeviceSignalQuality", c_uint),
        ("DeviceSignalStrength", c_uint),
    ]


class Utils:
    """Utility functions for handling pointers and structures"""
    
    @staticmethod
    def as_string(ptr: c_void_p) -> str:
        """Convert pointer to string"""
        if ptr:
            return cast(ptr, c_char_p).value.decode('ascii')
        return ""
    
    @staticmethod
    def to_int_ptr(msg: PassThruMsg) -> c_void_p:
        """Convert PassThruMsg to pointer"""
        return cast(pointer(msg), c_void_p)
    
    @staticmethod
    def as_msg_list(ptr: c_void_p, count: int) -> List[PassThruMsg]:
        """Convert pointer to list of PassThruMsg"""
        msg_list = []
        array_type = PassThruMsg * count
        array = cast(ptr, POINTER(array_type)).contents
        for i in range(count):
            msg_list.append(array[i])
        return msg_list
    
    @staticmethod
    def as_list(ptr: c_void_p, count: int, struct_type: type) -> list:
        """Convert pointer to list of structures"""
        result_list = []
        array_type = struct_type * count
        array = cast(ptr, POINTER(array_type)).contents
        for i in range(count):
            result_list.append(array[i])
        return result_list
    
    @staticmethod
    def as_struct(ptr: c_void_p, struct_type: type):
        """Convert pointer to structure"""
        return cast(ptr, POINTER(struct_type)).contents
    
    @staticmethod
    def as_nullable_struct(ptr: c_void_p, struct_type: type) -> Optional[any]:
        """Convert pointer to structure or None"""
        if not ptr:
            return None
        return cast(ptr, POINTER(struct_type)).contents
    
    @staticmethod
    def as_string_from_list(msg_list: List[PassThruMsg]) -> str:
        """Convert list of PassThruMsg to string"""
        result = ""
        for i, msg in enumerate(msg_list):
            result += f"{i} -------------------------------\n"
            result += msg.to_string()
            result += f"{i} -------------------------------\n"
        return result


# Example usage
if __name__ == "__main__":
    # Create a J2534 device instance
    device = J2534Device()
    device.name = "Test Device"
    device.function_library = "path/to/j2534.dll"
    
    # Create J2534 functions instance
    j2534 = J2534FunctionsExtended()
    
    # Load the library
    if j2534.load_library(device):
        print(f"Successfully loaded {device.name}")
        
        # Open device
        device_id = c_uint()
        result = j2534.pass_thru_open(None, device_id)
        
        if result == J2534Err.STATUS_NOERROR:
            print(f"Device opened with ID: {device_id.value}")
            
            # Connect to vehicle
            channel_id = c_uint()
            result = j2534.pass_thru_connect(
                device_id,
                ProtocolID.ISO15765,
                ConnectFlag.NONE,
                BaudRate.ISO15765_500000,
                channel_id
            )
            
            if result == J2534Err.STATUS_NOERROR:
                print(f"Connected with channel ID: {channel_id.value}")
                
                # Disconnect
                j2534.pass_thru_disconnect(channel_id.value)
            
            # Close device
            j2534.pass_thru_close(device_id)
        
        # Free library
        j2534.free_library()
    else:
        print("Failed to load library")
    
    def read_programming_voltage(self, device_id: c_int, voltage: c_int) -> J2534Err:
        try:
            input_ptr = c_void_p()
            output = c_int()
            
            voltage.value = self._j2534_dll_wrapper.ioctl(
                device_id, int(Ioctl.READ_PROG_VOLTAGE), input_ptr, byref(output)
            )
            
            return J2534Err.STATUS_NOERROR
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def five_baud_init(self, channel_id: c_int, target_address: c_ubyte,
                      keyword1: c_ubyte, keyword2: c_ubyte) -> J2534Err:
        try:
            input_ptr = c_void_p()
            output = c_void_p()
            
            input_array = SByteArray()
            output_array = SByteArray()
            input_array.num_of_bytes = 1
            output_array.num_of_bytes = 2
            
            return_value = J2534Err(self._j2534_dll_wrapper.ioctl(
                channel_id, int(Ioctl.FIVE_BAUD_INIT), byref(input_array), byref(output_array)
            ))
            
            return return_value
        except MemoryError:
            return J2534Err.ERR_OUT_OF_MEMORY
    
    def fast_init(self, channel_id: c_int, tx_msg: 'PassThruMsg', rx_msg: 'PassThruMsg') -> J2534Err:
        try:
            input_ptr = pointer(tx_msg)
            u_rx_msg = PassThruMsg()
            output = pointer(u_rx_msg)
            
            return_value = J2534Err(self._j2534_dll_wrapper.ioctl(
                channel_id, int(Ioctl.FAST_INIT), input_ptr, output
            ))
            
            if return_value == J2534Err.STATUS_NOERROR:
                rx_msg = u_rx_msg
            
            return return_value
        except MemoryError:
            return J2534Err.ERR