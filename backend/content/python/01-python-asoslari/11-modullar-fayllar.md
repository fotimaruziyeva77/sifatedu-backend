+++
title = "11-mavzu: modullar, fayllar va xatolarni ushlash"
summary = "import usullari, random va datetime, fayl bilan ishlash (with open) va try / except"
+++

::: slaydlar

###### Python darsi · 11-mavzu
# Modullar, fayllar va xatolar

random, datetime, fayl bilan ishlash va try / except

`import random` `with open(...)` `try:` nazariya + 3 ta amaliyot + viktorina

---

###### Bugungi reja
## Darsda nimalarni o'rganamiz?

### 01 Modullar

`import` usullari, `random`, `datetime`

### 02 Fayllar

Yozish, o'qish, oxiriga qo'shish

### 03 Xatolar

`try` / `except` — dastur yiqilmasin

### 04 Loyiha

Faylda saqlaydigan kundalik

---

###### 01 · Muammo
## Dastur yopilsa, ma'lumot yo'qoladi

### Faqat o'zgaruvchida {.qizil}

```python
ismlar = ["Ali", "Vali"]
ismlar.append("Laylo")
# dastur yopildi — ro'yxat yo'q!
```

|||

### Faylda {.yashil}

```python
with open("ismlar.txt", "a") as f:
    f.write("Laylo\n")
# ertaga ham shu yerda
```

Fayl diskda saqlanadi: dastur yopilsa ham yo'qolmaydi.

---

###### 02 · Modullar
## Modul ulashning 3 usuli

```python
import math
print(math.sqrt(16))        # 4.0

from math import pi, sqrt
print(sqrt(25))             # 5.0

import random as r
print(r.randint(7, 7))      # 7
```

|||

### import math

Butun modul: `math.sqrt`

### from math import sqrt

Faqat kerakli nom: `sqrt`

### import … as r

Qisqa nom: `r.randint`

---

###### 02 · Modullar
## random — tasodif

| Funksiya | Nima qiladi |
|---|---|
| `random.randint(1, 6)` | 1 dan 6 gacha butun son (ikkalasi ham kiradi) |
| `random.choice(royxat)` | Ro'yxatdan bitta tasodifiy element |
| `random.shuffle(royxat)` | Ro'yxatni aralashtiradi (o'zini) |
| `random.random()` | 0 va 1 orasidagi kasr son |

Zar, lotereya, viktorina savollarini aralashtirish, o'yinlar — hammasi `random` bilan.

---

###### 02 · Modullar
## datetime — sana va vaqt

```python
from datetime import date
bugun = date(2026, 10, 23)
navruz = date(2027, 3, 21)
print(bugun.year)                    # 2026
print((navruz - bugun).days)         # 149
print(bugun.strftime("%d.%m.%Y"))    # 23.10.2026
```

|||

### date.today()

Bugungi sana — kompyuter soati bo'yicha

### Ayirma

Ikki sana farqi: `.days` — kunlarda

### strftime

Sanani chiroyli ko'rinishda yozish

---

###### Amaliyot 1 · 10 daqiqa
## Tasodif va sana

1. Zarni 5 marta tashlang: `random.randint(1, 6)` (sikl bilan).
2. Ro'yxatdan tasodifiy «kun so'zi»ni tanlang (`random.choice`).
3. Tug'ilgan kuningizdan bugungacha necha kun o'tganini toping.
4. Bugungi sanani «23.10.2026» ko'rinishida chiqaring.

> **Yulduzli topshiriq:** harf va raqamlardan 8 belgili tasodifiy parol yasang (`random.choice` + sikl).

---

###### 03 · Fayllar
# Ma'lumotni faylda saqlaymiz

open() va with — yozish, o'qish, oxiriga qo'shish.

`open("fayl.txt", "w")` `with`

---

###### 03 · Fayllar
## Faylga yozish va o'qish

#### Kod

```python
with open("salom.txt", "w", encoding="utf-8") as f:
    f.write("Salom!\n")
    f.write("Python\n")

with open("salom.txt", encoding="utf-8") as f:
    matn = f.read()
print(matn)
```

|||

#### Ekranda

```text
Salom!
Python
```

`with` — ish tugagach fayl o'zi yopiladi. O'zbekcha harflar uchun `encoding="utf-8"`.

---

###### 03 · Fayllar
## Fayl rejimlari

| Rejim | Nima qiladi | Fayl yo'q bo'lsa |
|---|---|---|
| `"r"` | o'qish (standart) | `FileNotFoundError` |
| `"w"` | yozish — eski matnni **o'chiradi** | yangisini yaratadi |
| `"a"` | oxiriga qo'shish | yangisini yaratadi |

`"w"` bilan ochilgan fayl birinchi qatordayoq tozalanadi — ehtiyot bo'ling!

---

###### 03 · Fayllar
## Qatorma-qator o'qish

#### Kod

```python
with open("ismlar.txt", "w", encoding="utf-8") as f:
    f.write("Ali\nVali\nLaylo\n")

with open("ismlar.txt", encoding="utf-8") as f:
    for i, qator in enumerate(f, 1):
        print(i, qator.strip())
```

|||

#### Ekranda

```text
1 Ali
2 Vali
3 Laylo
```

`strip()` — qator oxiridagi `\n` ni olib tashlaydi.

---

###### 04 · Xatolar
## try / except — dastur yiqilmasin

### Himoyasiz {.qizil}

```python
son = int("abc")
print("Bu qator ishlamaydi")
```

```text
ValueError: invalid literal
for int() with base 10: 'abc'
```

|||

### try bilan {.yashil}

```python
try:
    son = int("abc")
except ValueError:
    print("Son kiriting!")
print("Dastur davom etadi")
```

```text
Son kiriting!
Dastur davom etadi
```

---

###### 04 · Xatolar
## Ko'p uchraydigan xato turlari

| Xato | Qachon | Misol |
|---|---|---|
| `ValueError` | noto'g'ri qiymat | `int("abc")` |
| `ZeroDivisionError` | nolga bo'lish | `10 / 0` |
| `FileNotFoundError` | fayl yo'q | `open("yoq.txt")` |
| `KeyError` | lug'atda kalit yo'q | `{}["a"]` |
| `IndexError` | ro'yxatda indeks yo'q | `[1, 2][5]` |
| `TypeError` | turlar mos emas | `"5" + 5` |

`except` dan keyin aniq xato turini yozing — boshqa xatolar yashirinib qolmasin.

---

###### 04 · Xatolar
## Xavfsiz kiritish: to'g'ri son kiritilguncha

#### Kod

```python
while True:
    try:
        yosh = int(input("Yosh: "))
        break
    except ValueError:
        print("Faqat son kiriting!")
print("Rahmat:", yosh)
```

|||

#### Ekranda

```text
Yosh: o'n yetti
Faqat son kiriting!
Yosh: 17
Rahmat: 17
```

`while` + `try` — eng ko'p ishlatiladigan andoza.

---

###### Amaliyot 2 · 10 daqiqa
## Xavfsiz kalkulyator

1. Ikki sonni `input()` bilan so'rang (`float`).
2. Son bo'lmasa — `ValueError`: «Son kiriting».
3. Ikkinchi son 0 bo'lsa — `ZeroDivisionError`: «Nolga bo'lib bo'lmaydi».
4. Natijani 2 xonagacha yaxlitlab chiqaring.

> **Yulduzli topshiriq:** har natijani `natijalar.txt` fayliga qo'shib boring (`"a"` rejim).

---

###### Amaliyot 3 · Mini loyiha · 15 daqiqa
## Kundalik

#### Kod

```python
from datetime import date
yozuv = input("Bugun nima qildingiz? ")
with open("kundalik.txt", "a", encoding="utf-8") as f:
    f.write(f"{date.today()}: {yozuv}\n")

with open("kundalik.txt", encoding="utf-8") as f:
    print(f.read())
```

|||

#### Endi o'zingiz davom ettiring

1. Yozuvlar sonini chiqaring.
2. Fayl yo'q bo'lsa — `FileNotFoundError` ni ushlang.
3. So'z bo'yicha qidirish qo'shing.
4. Menyu: yozish / o'qish / chiqish (`while True`).

---

###### 05 · Viktorina
## Kompyutersiz ayting: ekranda nima chiqadi?

### 1-savol

```python
from math import sqrt
print(sqrt(36))
```

### 2-savol

```python
try:
    print(10 / 0)
except ZeroDivisionError:
    print("nol")
```

### 3-savol

```python
try:
    x = int("12")
    print(x + 1)
except ValueError:
    print("xato")
```

### 4-savol

```python
import random
print(random.randint(5, 5))
```

### 5-savol

```python
from datetime import date
d = date(2026, 1, 10)
print((d - date(2026, 1, 1)).days)
```

### 6-savol

```python
try:
    print([1, 2][5])
except IndexError:
    print("yo'q")
```

---

###### 05 · Viktorina
## Javoblar: nechta to'g'ri topdingiz?

### 1-savol

`6.0`

`sqrt` doim float beradi.

### 2-savol

`nol`

Xato ushlandi — except ishladi.

### 3-savol

`13`

Xato yo'q — except ishlamadi.

### 4-savol

`5`

5 dan 5 gacha — faqat 5.

### 5-savol

`9`

10 - 1 = 9 kun.

### 6-savol

`yo'q`

5-indeks yo'q — IndexError ushlandi.

---

###### Xulosa va uyga vazifa
## Bugun nimani o'rgandik

### Esda qoladigan 4 narsa {.sariq}

- `import modul` yoki `from modul import nom`
- `with open(fayl, rejim, encoding="utf-8")`: `w`, `a`, `r`
- `try` / `except XatoTuri` — dastur yiqilmaydi
- `random` — tasodif, `datetime` — sana

|||

### Uyga vazifa {.qizil}

1. Talabalar fayli: yozish va o'qish
2. `bol(a, b)`: nolga bo'lishni ushlash
3. `son_ol(matn)`: `ValueError`
4. Ikki zar: `random`
5. Yangi yilgacha necha kun

Batafsil — platformadagi «Uy vazifasi» bo'limida.

::: ustozga

Dars rejasi (2 soat):
- 0–15 daq: 10-dars uy vazifasi (funksiyalar, return).
- 15–35 daq: modullar, random, datetime (3–6-slaydlar). Modulni «asboblar qutisi»ga o'xshating: import — qutini olib kelish.
- 35–45 daq: Amaliyot 1.
- 45–65 daq: fayllar (8–11-slaydlar). Fayl VS Code'da qayerda paydo bo'lishini ko'rsating (dastur ishga tushgan papka). "w" eski matnni o'chirishini jonli ko'rsating.
- 65–75 daq: tanaffus.
- 75–95 daq: try / except (12–14-slaydlar). Avval xatoni ataylab chiqaring, keyin ushlang.
- 95–110 daq: Amaliyot 2 va 3.
- 110–120 daq: viktorina, platformadagi test va uy vazifasi.

Ko'p uchraydigan xatolar: "w" bilan kerakli faylni o'chirib yuborish; encoding="utf-8" siz o'zbekcha harflar buzilishi (Windows'da); fayl boshqa papkada qidirilishi (FileNotFoundError); except'ni xato turisiz yozib, barcha xatolarni yashirish; with'dan tashqarida faylni o'qishga urinish.

::: test

? random modulini ulash uchun nima yoziladi?
+ import random
- include random
- using random
- random.import()
> Modul import bilan ulanadi.

? Quyidagi kod nima chiqaradi?
```python
from math import sqrt
print(sqrt(49))
```
+ 7.0
- 7
- 49
- Xato beradi
> sqrt doim float qaytaradi; from ... import bilan math. yozilmaydi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
import random
x = random.randint(1, 1)
print(x)
```
= 1
> 1 dan 1 gacha — faqat 1.

? Faylga eski matnni o'chirib yozish uchun qaysi rejim ishlatiladi?
+ "w"
- "r"
- "a"
- "x"
> "w" — write: fayl tozalanib, qaytadan yoziladi.

? Fayl oxiriga qo'shish uchun qaysi rejim ishlatiladi?
+ "a"
- "w"
- "r"
- "e"
> "a" — append: eski matn saqlanadi.

? with open(...) as f: yozuvining afzalligi nima?
+ Ish tugagach fayl o'zi yopiladi
- Fayl tezroq ochiladi
- Faylni o'chiradi
- Hech qanday farqi yo'q
> with bloki tugashi bilan fayl avtomatik yopiladi.

? Quyidagi kod nima chiqaradi?
```python
try:
    print(int("5a"))
except ValueError:
    print("xato")
```
+ xato
- 5
- 5a
- ValueError
> "5a" ni songa o'girib bo'lmaydi — except ishlaydi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
try:
    print(8 / 2)
except ZeroDivisionError:
    print("nol")
```
= 4.0
> Xato yo'q — try ichidagi print ishlaydi.

? Quyidagi kod nima chiqaradi?
```python
d = {"a": 1}
try:
    print(d["b"])
except KeyError:
    print("kalit yo'q")
```
+ kalit yo'q
- None
- 1
- KeyError
> "b" kaliti yo'q — KeyError ushlandi.

? Quyidagi kod qaysi xatoni beradi?
```python
open("yoq_fayl.txt")
```
+ FileNotFoundError
- ValueError
- KeyError
- TypeError
> O'qish uchun ochilayotgan fayl mavjud emas.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
from datetime import date
print((date(2026, 3, 1) - date(2026, 2, 1)).days)
```
= 28
> 2026-yil fevrali — 28 kun.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
import math as m
print(m.floor(3.9))
```
= 3
> as m — modulga qisqa nom; floor pastga yaxlitlaydi.

? Faylni qatorma-qator o'qish kodini tartibga qo'ying.
1. with open("ismlar.txt", encoding="utf-8") as f:
2. for qator in f:
3. print(qator.strip())

? Xato turini sababi bilan moslang:
ValueError :: int("abc")
ZeroDivisionError :: 10 / 0
FileNotFoundError :: yo'q faylni ochish
IndexError :: ro'yxatda yo'q indeks

::: uy-vazifasi

5 ta topshiriq — hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying (yoki .py fayl biriktiring). Har topshiriq oldidan izoh yozing: # 1-topshiriq, # 2-topshiriq va h.k.
Fayllarni encoding="utf-8" bilan oching.

1-topshiriq. Talabalar fayli
talabalar.txt fayliga 3 ta ism yozing: Ali, Vali, Laylo (har biri alohida qatorda). Keyin faylni o'qib, ismlarni raqamlab chiqaring va oxirida jami sonini yozing.

Kutilgan natija:
1. Ali
2. Vali
3. Laylo
Jami: 3

2-topshiriq. Xavfsiz bo'lish
bol(a, b) funksiyasi a / b ni qaytarsin; b nol bo'lsa (ZeroDivisionError) — «Nolga bo'lib bo'lmaydi» matnini qaytarsin. bol(10, 2) va bol(5, 0) ni chiqaring.

Kutilgan natija:
5.0
Nolga bo'lib bo'lmaydi

3-topshiriq. Son olish
son_ol(matn) — matnni int ga o'girib qaytarsin; o'girib bo'lmasa (ValueError) — None qaytarsin. son_ol("42") va son_ol("qirq") ni chiqaring.

Kutilgan natija:
42
None

4-topshiriq. Ikki zar
random bilan ikkita zar tashlang (1–6) va natijani chiqaring. Har safar boshqacha chiqadi — ko'rinishi shunday bo'lsin.

Kutilgan natija (masalan):
Zarlar: 3 va 5, yig'indi: 8

5-topshiriq. Yangi yilgacha
datetime.date bilan 2026-yil 23-oktabrdan 2026-yil 31-dekabrgacha necha kun qolganini hisoblang.

Kutilgan natija:
69 kun
