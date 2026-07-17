Shannon LTE CA editor
=====================

A Python/Tkinter GUI editor to modify LTE CA combos on Pixel devices, featuring useful tools to save editing effort.

<img width="1000" alt="image" src="https://github.com/user-attachments/assets/bdec9472-ac56-4627-b4d4-c47ae4276a1f" />


Features
--------

- Import/export LTE .binarypb files directly
- Import/export as protobuf .txt formats
- Import/export S5300 carrierconfig confseq bundles and portable JSON
- View LTE combinations in a searchable table w/plmn filtering
- Edit LTE bands, assign DL/UL bw classes, MIMO, BCS, and plmn mappings
- Add, duplicate, delete, and reorder any combos
- Add, delete, and reorder CCs in each combo
- Auto-generate CA combos and auto UL assignment to save time!
- Prune combos to reduce message size with band filter and/or intra-band CA exclusion
- Apply conf_id bitmasks (plmn mapping) to all combinations or selected bands
- Validate and automatically repair any typos or unsupported configurations, such as low-band 4x4 or illegal B7, B38 uplink assignment, etc.

Validation Checks
-----------------

After editing, you can use the ```Validation``` function to check for errors/typos/bad configurations, such as:

- Duplicates
- Missing uplink
- B7/B38 uplink assignments if a combo contains 7+38
- Accidental uplink assignments on SDL bands
- Exceed 24 spatial streams
- Unsupported low-band combinations (only 20+28 is supported)
- Invalid DL/UL bw classes
- 4x4 DL MIMO assignments on low bands

Some of the errors can be fixed automatically, while some can only be highlighted for manual review.

Running
-------
For Windows users, you can download the executable from the **Releases** section and run it directly without installing any dependencies. Alternatively, you can run `main.py`.

From the project folder:

    py main.py

However, you will need...

- Python 3.10+
- protobuf
- lz4
- PyInstaller (if you want to compile your own version)

Install dependencies with:

    py -m pip install protobuf lz4 pyinstaller

S5300 confseq support
---------------------

Older Shannon Pixel devices such as S5300 store LTE CA combinations as NV items
inside carrierconfig confseq profiles instead of a standalone `.binarypb` file.
Use **File > Import S5300 confseq folder** and select a complete `confseqs`
directory. The editor detects the available `lte_ca` families and reads the
combo count, bands, DL/UL classes, BCS, and both PLMN category bitmaps.

Each family is exported as its six primary/mirror profiles. Existing common NVs,
profile metadata, CLZ4 metadata, empty value groups, and signed 64-bit category
masks are preserved. The exporter reloads the generated profiles before reporting
success. JSON is an interchange format for combo data; raw confseq export still
requires a matching imported confseq bundle as the device-specific template.

Validate all detected families without opening the GUI:

    py validate_s5300.py path\to\carrierconfig\confseqs

Using the auto combo generator
--------------------------
<img width="600" alt="image" src="https://github.com/user-attachments/assets/0d47df04-569f-405a-97a7-8d389ef6af46" />


Input a "large" combo such as
```1+1+3+3+8B+28+32+40D+41```.
The function will generate fallback sets such as ```1+1```, ```1+3```, ```1+3+8```, ```1+3+8B```, ```1+1+3+28```, ```1+40```. ```1+40C```etc, and assign the appropriate bw classes and mimo capability to each of them automatically. Most networks do not support more than 5CA, hence Max CC is 5 by default. BCS determines the allowable bandwidths in a combo, and in most cases, BCS=0 works fine except for cases such as ```1+3``` where B1 can't be 3 MHz without BCS=0,1.

If a combo already exists, it will be skipped to avoid duplication.

The generator automatically avoids "impossible" configurations such as:

- Anything besides ```20+28``` for low band CA
- 4x4 MIMO on low bands or B21
- Uplink on SDL
- Uplink on B7 or B38 if the combo contains ```7+38```

If a combo contains more than 24 spatial streams, the algorithm will generate subvariants with nerfed MIMO automatically. 
For example, ```1C+3C+7C+28``` with MIMO ```4+4+4+4+4+4+2 (26)``` will be broken into the following MIMO subsets:
- ```2+2+4+4+4+4+2```
- ```4+4+2+2+4+4+2```
- ```4+4+4+4+2+2+2```

Uplink class A will be assigned to the generated combos automaticall. For ULCA, there are several options to choose from:

- ```None selected``` only intraband-contiguous ULCA such as 3C, 7C, 40C, 41C.
- ```Allow FDD A+A``` Both intra-band and inter-band non-contiguous ULCA for FDD only. Inter-band A+A works fine for most networks.
- ```Allow TDD A+A``` Very uncommon.
- ```Allow TDD+FDD``` Unlikely to work.

Bandwidth classes and MIMO per CC component
-----------------

### 1. Bandwidth Classes (CC Count)
The bandwidth class determines the number of aggregated Component Carriers (CC) for intra-band contiguous CA:

| Class | # Component Carriers (CC) |
| :---: | :--- |
| **A** | 1 |
| **B** | 2 (≤20 MHz total) |
| **C** | 2 |
| **D** | 3 |
| **E** | 4 |
| **F** | 5 |

Note: Class B is very uncommon

The **least-significant bit** determines the DL MIMO mode. You can instantly identify this by seeing if the last decimal is even or odd:

For example:

```text
32768 --> 1000 0000 0000 0000 --> Class A, 2x2 MIMO (Even)
32769 --> 1000 0000 0000 0001 --> Class A, 4x4 MIMO (Odd)
 8192 --> 0010 0000 0000 0000 --> Class C, 2x2 MIMO (Even)
 8193 --> 0010 0000 0000 0001 --> Class C, 4x4 MIMO (Odd)
```

Combo Pruning
-------------
<img width="612" height="177" alt="image" src="https://github.com/user-attachments/assets/b801740e-f111-4c13-b7b5-001a05376643" />

This function will come in handy if your network does not configure ```requestedFrequencyBands-r11```. Without this parameter, your device can only report up to 128 combos in the ```UE Capability Information``` message and the rest will be cut off. 

To solve this problem, use this Combo pruning function to reduce the total combo count by:

- Only including the LTE bands that you need
- Removing unnecessary intra-band configurations such as ```3C``` or ```3+3```

**PRO TIP:** The combinations in the `UE Capability Information` message follow the exact same order as they appear in the `.binarypb` file. Therefore, the first 128 combos should be essential.

PLMN mapping
-------------
<img width="900" alt="image" src="https://github.com/user-attachments/assets/ccf6fff1-0557-48cf-a75a-6493c6e1ffe1" />

Each combo is mapped to one or more ```conf_id``` values, and each ```conf_id``` represents a group of PLMNs defined in ```ap_plmn_mapping.binarypb```.

The valid conf_id range is 0 to 95. Because 96 bits are required to represent all possible ```conf_id``` values, the mapping is split across two bitmask fields:

- Conf ID 1 is a ```uint64``` bitmask representing ```conf_id``` 0 to 63.
- Conf ID 2 is a ```uint32``` bitmask representing ```conf_id``` 64 to 95 with a +64 offset
  
For example, the ```conf_id``` values for TMO, DISH, and ROGERS are 2, 6, and 7 respectively. If a combo is mapped to these three PLMN groups, the value of ```Conf ID 1``` will be 196 because:

2^2 = 4

2^6 = 64

2^7 = 128

4 + 64 + 128 = 196

In binary form:

```text
196 = 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 0000 1100 0100
```

Luckily, you can just use the ```Apply conf_id to combos``` function to calculate the conf_id values and apply it to certain bands or all combos. If your PLMN does not belong to any conf_id, you must manually edit ```ap_plmn_mapping.binarypb```

<img width="445" height="280" alt="image" src="https://github.com/user-attachments/assets/2fe087c6-d83d-4896-aad0-4322541dfd01" />

Building your own executable
-----------------------------

From the project folder:

    py -m PyInstaller --noconfirm --onefile --windowed --name "Shannon LTE CA editor" --collect-all google.protobuf main.py

The executable will be created in the dist folder.

Project Files
-------------

```main.py```
    Main Tkinter application.

```utils.py```
    Protobuf parsing, import/export, data models, UL generation,
    validation, repair, and other LTE utilities.

```custom_utils.py```
    Custom-combination generation, band filtering, exclusion rules,
    DL MIMO generation, and hardware-limit handling.

```tools_ui.py```
    Dialog windows for the auto combo generator, combo pruning, conf_id mapping, and
    validation.

```conf_id.py```
    conf_id names and bitmask conversion helpers.

Important Notes
---------------

- Always Keep main.py, utils.py, custom_utils.py, tools_ui.py, and conf_id.py in the same folder.
- Validation only fixes the combo format and does not guarantee network compatibility.
- Test unusual combos at your own risk.

Credits / Acknowledgements
----------
Protobuf definition obtained from [uecapabilityparser](https://github.com/HandyMenny/uecapabilityparser)
