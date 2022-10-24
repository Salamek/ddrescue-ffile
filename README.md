# ddrescue-ffile

[![Donate](https://img.shields.io/badge/Donate-PayPal-green.svg)](https://www.paypal.com/cgi-bin/webscr?cmd=_donations&business=D8LQ4XTBLV3C4&lc=CZ&item_number=SalamekPplMyApi&currency_code=EUR)

Tool for identifying corrupted files in image created by ddrescue

# Always run this tool only on copy of your image! Always have a backup!


## Usage

```
sudo ddrescue-ffile.py [image] [logfile]

Like:
sudo ddrescue-ffile.py ~/rescued-sda.img ~/ddrescue-sda.log

Where:
~/rescued-sda.img is path to rescued image
~/ddrescue-sda.log is rescue log created by ddrescue
```
