# mai22maitouch
Convert mai2touch serial data to 'old cab' maimai game(e.g. maimai FiNALE) touch, auto pass start check.  
Support ADX Serial Mode, HDX, [mai_pico](https://github.com/whowechina/mai_pico), [Mai2Touch](https://github.com/Sucareto/Mai2Touch/blob/main/Mai2Touch) and other controller with native serial touch.  
# Attention, all of these codes are basically generated by AI(DeepSeek&GPT-4o)
I really don't know if there's better way, I'm not good at programming, this is only for my own need. 
**Thanks to [@clansty](https://github.com/clansty), now we have correct Individual bit breakdown for mai2, already updated. AI is really not good at orders/tables/numbers, they will make everything messed up:(**  
# How to Use
You only need mai22maitouch.py, pther files is for testing.  
1.Use [com0com](https://github.com/vovsoft/com0com) to generate pair COM33<->COM3.
3 serial ports for mai22maitouch, COM13 for your device(edit in Device Manager), COM33(virtual) for python to write in data, COM3(virtual) for game to read.
2.Edit GrooveMaster.ini (config for maimai_dump_.exe), make sure DEV 1 and NO_SERIAL 0. I don't know much about how micetools work, you can try by yourself if you use micetools.  
3.Run mai22maitouch.py，it will start listening COM3 and COM13 (connect and config your controller's port first!).  
4.Start your game, the TouchSensor check will be a GOOD=).  
You may put a # before all the "print()" to disable printing log to console, which may optimize speed and latency.
# It works!
Tested with SDEY1.99B, cool.  
# How it works
Ref:[Sucareto/Mai2Touch-GitHub](https://github.com/Sucareto/Mai2Touch/blob/main/Mai2Touch/README.md)  
Ref:[The MaiMai Touchscreen-bsnk.me](https://sega.bsnk.me/maimai/touch/#packet-format)  
The Individual bit breakdown for mai2  
| Byte | 7  | 6  | 5  | 4  | 3  | 2  | 1  | 0  | ASCII |
|------|----|----|----|----|----|----|----|----|-------|
| 0    | 0  | 0  | 1  | 0  | 1  | 0  | 0  | 0  | `(`   |
| 1    | 0  | 0  | 0  | A5  | A4 | A3 | A2 | A1 | _varies_ |
| 2    | 0  | 0  | 0  | B2 | B1 | A8 | A7 | A6 | _varies_ |
| 3    | 0  | 0  | 0  | B7 | B6 | B5 | B4 | B3 | _varies_ |
| 4    | 0  | 0  | 0  | D2 | D1 | C2 | C1 | B8 | _varies_ |
| 5    | 0  | 0  | 0  | D7 | D6 | D5 | D4 | D3 | _varies_ |
| 6    | 0  | 0  | 0  | E4 | E3 | E2 | E1 | D8 | _varies_ |
| 7    | 0  | 0  | 0  | 0  | E8 | E7 | E6 | E5 | _varies_ |
| 8    | 0  | 0  | 1  | 0  | 1  | 0  | 0  | 1  | `)`   |
  
The Individual bit breakdown for mai  
| Byte | P1/2 | 7  | 6  | 5  | 4  | 3  | 2  | 1  | 0  | ASCII |
|------|------|----|----|----|----|----|----|----|----|-------|
| 0    |      | 0  | 0  | 1  | 0  | 1  | 0  | 0  | 0  | `(`   |
| 1    | P1   | 0  | 1  | 0  | 0  | B2 | A2 | B1 | A1 | _varies_ |
| 2    | P1   | 0  | 1  | 0  | 0  | B4 | A4 | B3 | A3 | _varies_ |
| 3    | P1   | 0  | 1  | 0  | 0  | B6 | A6 | B5 | A5 | _varies_ |
| 4    | P1   | 0  | 1  | 0  | C  | B8 | A8 | B7 | A7 | _varies_ |
| 5    |      | 0  | 1  | 0  | 0  | 0  | 0  | 0  | 0  | `@`   |
| 6    |      | 0  | 1  | 0  | 0  | 0  | 0  | 0  | 0  | `@`   |
| 7    | P2   | 0  | 1  | 0  | 0  | B2 | A2 | B1 | A1 | _varies_ |
| 8    | P2   | 0  | 1  | 0  | 0  | B4 | A4 | B3 | A3 | _varies_ |
| 9    | P2   | 0  | 1  | 0  | 0  | B6 | A6 | B5 | A5 | _varies_ |
| 10   | P2   | 0  | 1  | 0  | C  | B8 | A8 | B7 | A7 | _varies_ |
| 11   |      | 0  | 1  | 0  | 0  | 0  | 0  | 0  | 0  | `@`   |
| 12   |      | 0  | 1  | 0  | 0  | 0  | 0  | 0  | 0  | `@`   |
| 13   |      | 0  | 0  | 1  | 0  | 1  | 0  | 0  | 1  | `)`   |
  
I think that's enough.
