
This repository will be used for the Cisco Live US DEVNET-2049 session.

Sample code included: 
- DEVNET_2049_DDA_CL.py
- DEVNET_2049_DDA_CL.html - PyDoc generated documentation
- DEVNET_2049_DDA_CL.pdf - Application run output
- Manufacturing plant floor maps files from CMX, and annotated with the AP and AGV locations are included.

Automated Guided Vehicles (AGVs) are critical to the engine manufacturing process. Each AGV hosts one or more
Programmable Logic Controllers (PLCs) that use wireless to communicate with Human Machine Interfaces (HMI's)
connected to the plant automation network. Manufacturing lines will stop if there is a interruption of communication.

We can automate the steps required to detect and quick start the troubleshooting of the disconnected PLC.
The script will:

- Find out the disconnected AGV number and the IP address using a database lookup
- Provide the last known location information from CMX
- Access Point reachability status
- Access switch reachability and switchport status
- Path visualization between PLC and HMI
- Create a Spark Room and invite engineering resources
- Notification using Tropo

This approach could be applied for monitoring of any critical wireless assets in healthcare, financial, retail and utilities.
