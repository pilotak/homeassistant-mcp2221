# HomeAssistant - MCP2221 integration

Integration that adds missing GPIOs (input, output, ADC) to your NUC or Proxmox-based installation over USB.

```yaml
# Example configuration.yaml entry
mcp2221:
  - switches:
      - name: "Output 0"
        pin: 0
        unique_id: out0
      - name: "Output 1"
        pin: 1
        unique_id: out1
    binary_sensors:
      - name: "Input 2"
        pin: 2
        unique_id: in2
        device_class: door
      - name: "Input 3"
        pin: 3
        unique_id: in3
        icon: mdi:electric-switch
    # adc:
    #   ref: 4.096
    #   sensors:
    #     - name: "voltage"
    #       pin: 3
    #       unique_id: adc3
```

### Full examples

<details>
<summary>1️⃣Switch (output) & multiple devices</summary>
You can also specift multiple device, just adjust the index (`dev`) or even specify different PID/VID

```yaml
mcp2221:
  - dev: 0
    pid: 0x00DD
    vid: 0x04D8
    switches:
      - name: "Output 0"
        pin: 0
        unique_id: output_0_0
        icon: mdi:toggle-switch
  - dev: 1
    switches:
      - name: "Output 0"
        pin: 0
        unique_id: output_1_0
        icon: mdi:toggle-switch
```

</details>

<details>
<summary>2️⃣Binary sensor (input)</summary>
❗Don't leave pin floating

```yaml
mcp2221:
  binary_sensors:
    - name: "Input 1"
      pin: 1
      inverted: True
      unique_id: input_0
      icon: mdi:toggle-switch
      scan_interval: 10
      device_class: door
```

</details>

<details>
<summary>3️⃣Sensor (ADC)</summary>
Only pins GP1-GP3, result is 10-bit (0-1023)

You can also adjust the result, example here is when power supply is 3.3V

```yaml
mcp2221:
  adc:
    ref: "VDD" # or 1.024, 2.048, 4.096
    sensors:
      - name: "Battery voltage"
        pin: 3
        unique_id: battery_voltage
        scan_interval: 50
        icon: mdi:car-battery
        device_class: voltage
        unit_of_measurement: V
        value_template: "{{ value * 3.3 / 1023}}"
```

</details>
