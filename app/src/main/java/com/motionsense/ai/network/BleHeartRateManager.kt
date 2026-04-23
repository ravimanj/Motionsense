package com.motionsense.ai.network

import android.annotation.SuppressLint
import android.bluetooth.*
import android.bluetooth.le.ScanCallback
import android.bluetooth.le.ScanFilter
import android.bluetooth.le.ScanResult
import android.bluetooth.le.ScanSettings
import android.content.Context
import android.os.Handler
import android.os.Looper
import android.os.ParcelUuid
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import java.util.UUID

@SuppressLint("MissingPermission")
class BleHeartRateManager private constructor(private val context: Context) {

    companion object {
        @Volatile
        private var instance: BleHeartRateManager? = null

        fun getInstance(context: Context): BleHeartRateManager =
            instance ?: synchronized(this) {
                instance ?: BleHeartRateManager(context.applicationContext).also { instance = it }
            }

        // Standard BLE Heart Rate UUIDs
        val HR_SERVICE_UUID: UUID = UUID.fromString("0000180D-0000-1000-8000-00805f9b34fb")
        val HR_MEASUREMENT_CHAR_UUID: UUID = UUID.fromString("00002A37-0000-1000-8000-00805f9b34fb")
        val CLIENT_CHARACTERISTIC_CONFIG_UUID: UUID = UUID.fromString("00002902-0000-1000-8000-00805f9b34fb")
    }

    private val bluetoothManager: BluetoothManager = context.getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager
    private val bluetoothAdapter: BluetoothAdapter? = bluetoothManager.adapter
    private var bluetoothGatt: BluetoothGatt? = null
    
    private var isScanning = false
    private val handler = Handler(Looper.getMainLooper())
    
    // State flows for UI
    private val _bpm = MutableStateFlow(0)
    val bpm: StateFlow<Int> = _bpm
    
    private val _connectionState = MutableStateFlow("Disconnected")
    val connectionState: StateFlow<String> = _connectionState

    // Callback for discovery in SetupActivity
    var onDeviceDiscovered: ((BluetoothDevice, Int) -> Unit)? = null

    private val scanCallback = object : ScanCallback() {
        override fun onScanResult(callbackType: Int, result: ScanResult) {
            super.onScanResult(callbackType, result)
            onDeviceDiscovered?.invoke(result.device, result.rssi)
        }
    }

    private val gattCallback = object : BluetoothGattCallback() {
        override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                if (newState == BluetoothProfile.STATE_CONNECTED) {
                    _connectionState.value = "Connected to ${gatt.device.name ?: "HR Monitor"}"
                    // Save MAC address for auto-reconnect
                    context.getSharedPreferences("MotionSensePrefs", Context.MODE_PRIVATE)
                        .edit().putString("last_ble_mac", gatt.device.address).apply()
                        
                    gatt.discoverServices()
                } else if (newState == BluetoothProfile.STATE_DISCONNECTED) {
                    _connectionState.value = "Disconnected"
                    _bpm.value = 0
                    gatt.close()
                }
            } else {
                _connectionState.value = "Error $status"
                gatt.close()
            }
        }

        override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
            if (status == BluetoothGatt.GATT_SUCCESS) {
                val service = gatt.getService(HR_SERVICE_UUID)
                if (service != null) {
                    val characteristic = service.getCharacteristic(HR_MEASUREMENT_CHAR_UUID)
                    if (characteristic != null) {
                        gatt.setCharacteristicNotification(characteristic, true)
                        // Write to CCCD to enable notifications
                        val descriptor = characteristic.getDescriptor(CLIENT_CHARACTERISTIC_CONFIG_UUID)
                        if (descriptor != null) {
                            descriptor.value = BluetoothGattDescriptor.ENABLE_NOTIFICATION_VALUE
                            gatt.writeDescriptor(descriptor)
                        }
                    }
                }
            }
        }

        override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
            if (characteristic.uuid == HR_MEASUREMENT_CHAR_UUID) {
                val hrValue = parseHeartRate(characteristic.value)
                _bpm.value = hrValue
            }
        }
    }

    fun startScan() {
        if (bluetoothAdapter == null || !bluetoothAdapter.isEnabled) return
        if (isScanning) return
        
        val scanner = bluetoothAdapter.bluetoothLeScanner ?: return
        
        // Filter only Heart Rate Service devices
        val filter = ScanFilter.Builder()
            .setServiceUuid(ParcelUuid(HR_SERVICE_UUID))
            .build()
            
        val settings = ScanSettings.Builder()
            .setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY)
            .build()

        isScanning = true
        _connectionState.value = "Scanning..."
        scanner.startScan(listOf(filter), settings, scanCallback)
        
        // Stop scan after 10 seconds
        handler.postDelayed({ stopScan() }, 10000)
    }

    fun stopScan() {
        if (!isScanning) return
        isScanning = false
        if (_connectionState.value == "Scanning...") {
            _connectionState.value = "Scan Finished"
        }
        bluetoothAdapter?.bluetoothLeScanner?.stopScan(scanCallback)
    }

    fun connectToDevice(device: BluetoothDevice) {
        stopScan()
        _connectionState.value = "Connecting..."
        bluetoothGatt = device.connectGatt(context, false, gattCallback)
    }

    fun autoReconnect() {
        val prefs = context.getSharedPreferences("MotionSensePrefs", Context.MODE_PRIVATE)
        val lastMac = prefs.getString("last_ble_mac", null)
        if (lastMac != null && bluetoothAdapter != null && bluetoothAdapter.isEnabled) {
            try {
                val device = bluetoothAdapter.getRemoteDevice(lastMac)
                connectToDevice(device)
            } catch (e: Exception) {
                _connectionState.value = "Auto-reconnect failed"
            }
        }
    }

    fun disconnect() {
        bluetoothGatt?.disconnect()
    }

    /**
     * Parses the Heart Rate Measurement characteristic byte array
     * following the Bluetooth SIG profile specification.
     */
    private fun parseHeartRate(value: ByteArray?): Int {
        if (value == null || value.isEmpty()) return 0
        
        // The first byte contains the flags
        val flags = value[0].toInt()
        
        // Bit 0 checks if the HR format is UINT8 (0) or UINT16 (1)
        val isFormat16Bit = (flags and 0x01) != 0
        
        return if (isFormat16Bit) {
            if (value.size >= 3) {
                (value[1].toInt() and 0xFF) or ((value[2].toInt() and 0xFF) shl 8)
            } else 0
        } else {
            if (value.size >= 2) {
                value[1].toInt() and 0xFF
            } else 0
        }
    }
}
