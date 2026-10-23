+++
title = "4-mavzu: math metodlari"
summary = "Tayyor funksiyalar (abs, round, min, max, sum, pow), math moduli va yaxlitlash"
+++

::: slaydlar

###### Python darsi · 4-mavzu
# Sonlar va math moduli

Tayyor funksiyalar, yaxlitlash, ildiz va daraja

`import math` `round(3.14159, 2)` nazariya + 3 ta amaliyot + viktorina

---

###### Bugungi reja
## Darsda nimalarni o'rganamiz?

### 01 Tayyor funksiyalar

`abs`, `round`, `min`, `max`, `sum`, `pow`

### 02 math moduli

`import math`: `sqrt`, `pi`, `factorial`

### 03 Yaxlitlash

`round`, `floor`, `ceil` va `int` farqi

### 04 Hayotiy hisoblar

Aylana, avtobuslar, narxlar

---

###### 01 · Muammo
## 529 ning ildizi nechchi?

### Qo'lda taxmin {.qizil}

```python
print(20 * 20)    # 400
print(25 * 25)    # 625
print(23 * 23)    # 529
# uch urinishda topdik...
```

|||

### math bilan {.sariq}

```python
import math
print(math.sqrt(529))    # 23.0
```

Python'da yuzlab tayyor funksiya bor — hammasini o'zimiz yozib o'tirmaymiz.

---

###### 02 · Tayyor funksiyalar
## import shart emas: 6 ta tayyor funksiya

### Modul

```python
abs(-12)          # 12
```

### Yaxlitlash

```python
round(7.6)        # 8
```

### Daraja

```python
pow(3, 2)         # 9
```

### Eng katta

```python
max(4, 9, 2)      # 9
```

### Eng kichik

```python
min(5, -1, 3)     # -1
```

### Yig'indi

```python
sum([1, 2, 3, 4])  # 10
```

---

###### 02 · Tayyor funksiyalar
## round() — yaxlitlash

```python
print(round(7.6))          # 8
print(round(7.4))          # 7
print(round(3.14159, 2))   # 3.14
print(round(2.5))          # 2
print(round(3.5))          # 4
```

|||

### round(x)

Eng yaqin butun son

### round(x, 2)

Verguldan keyin 2 xona

### Teng yarim

Juft songa: 2.5 → 2, 3.5 → 4

---

###### 02 · Tayyor funksiyalar
## min, max va sum ro'yxat bilan

```python
baholar = [5, 3, 4, 5]
print(max(baholar))                  # 5
print(min(baholar))                  # 3
print(sum(baholar))                  # 17
print(sum(baholar) / len(baholar))   # 4.25
```

|||

### Ro'yxat [ ]

Bir nechta son bitta nomda. Batafsil — 6-darsda.

### O'rtacha

Yig'indi ÷ soni: `sum / len`

---

###### Amaliyot 1 · 10 daqiqa
## Baholar va farqlar

1. `baholar = [4, 5, 3, 5, 4]` ro'yxatini yarating.
2. Eng yuqori va eng past bahoni chiqaring (`max`, `min`).
3. O'rtacha bahoni 2 xonagacha yaxlitlab chiqaring (`round`).
4. 15 va 42 orasidagi farqni manfiy chiqmaydigan qilib hisoblang (`abs`).

> **Yulduzli topshiriq:** `pow(2, 10)` va `2 ** 10` natijalarini solishtiring. Farqi bormi?

---

###### 03 · math moduli
# Modul — tayyor asboblar qutisi

import bilan ulaymiz, nuqta orqali ishlatamiz.

`import math` `math.sqrt(16)`

---

###### 03 · math moduli
## math'dagi eng kerakli asboblar

| Funksiya | Misol | Natija |
|---|---|---|
| `math.sqrt(x)` | `math.sqrt(81)` | `9.0` |
| `math.pi` | `math.pi` | `3.141592653589793` |
| `math.ceil(x)` | `math.ceil(2.1)` | `3` |
| `math.floor(x)` | `math.floor(2.9)` | `2` |
| `math.factorial(n)` | `math.factorial(4)` | `24` |
| `math.pow(x, y)` | `math.pow(2, 3)` | `8.0` |

`math.sqrt` va `math.pow` doim **float** qaytaradi: 9 emas, 9.0.

---

###### 03 · math moduli
## Yaxlitlashning 4 yo'li

| Son | `int()` | `round()` | `math.floor()` | `math.ceil()` |
|---|---|---|---|---|
| `2.1` | `2` | `2` | `2` | `3` |
| `2.5` | `2` | `2` | `2` | `3` |
| `2.7` | `2` | `3` | `2` | `3` |
| `-2.5` | `-2` | `-2` | `-3` | `-2` |

`int` — kasrni kesadi, `floor` — pastga, `ceil` — yuqoriga, `round` — eng yaqiniga.

---

###### 03 · math moduli
## Ildiz, daraja, faktorial

```python
import math
print(math.sqrt(25))        # 5.0
print(2 ** 10)              # 1024
print(pow(2, 10))           # 1024
print(25 ** 0.5)            # 5.0
print(math.factorial(5))    # 120
```

|||

### sqrt — kvadrat ildiz

Natija doim float

### ** va pow

Bir xil ish qiladi

### factorial

5! = 1 × 2 × 3 × 4 × 5

---

###### 03 · math moduli
## Diqqat: kasr sonlar aniq emas

### Kutilmagan natija {.qizil}

```python
print(0.1 + 0.2)          # 0.30000000000000004
print(0.1 + 0.2 == 0.3)   # False
```

|||

### Yechim {.yashil}

```python
print(round(0.1 + 0.2, 2))   # 0.3
```

Kompyuter kasrni ikkilik sanoqda saqlaydi — kichik xato bo'ladi. Pul hisobida `round()` ishlating.

---

###### 04 · Hayotiy hisoblar
## Aylana: uzunlik va yuza

#### Kod

```python
import math
r = 5
uzunlik = 2 * math.pi * r
yuza = math.pi * r ** 2
print(round(uzunlik, 2))
print(round(yuza, 2))
```

|||

#### Ekranda

```text
31.42
78.54
```

Formulalar: uzunlik — 2πr, yuza — πr². `math.pi` aniqroq: 3.14 emas.

---

###### 04 · Hayotiy hisoblar
## Nechta avtobus kerak?

```python
import math
oquvchilar = 47
joy = 20
print(oquvchilar / joy)              # 2.35
print(math.ceil(oquvchilar / joy))   # 3
```

|||

### 2.35 ta avtobus?

Yarim avtobus bo'lmaydi — yuqoriga yaxlitlaymiz

### math.ceil

Har doim yuqoriga: 2.35 → 3

---

###### Amaliyot 2 · 10 daqiqa
## Geometriya

1. Kvadrat yuzasi 144 — tomonini toping (`math.sqrt`).
2. Radiusi 3 bo'lgan aylana yuzasini 2 xonagacha hisoblang.
3. 100 ta daftar qutilarga 12 tadan joylanadi: nechta quti kerak? (`math.ceil`)
4. 5! ni `math.factorial` bilan hisoblang.

> **Yulduzli topshiriq:** to'g'ri burchakli uchburchakning katetlari 9 va 12. Gipotenuzani toping: √(a² + b²).

---

###### Amaliyot 3 · Mini loyiha · 15 daqiqa
## Taksi narxi

#### Kod

```python
import math
km = float(input("Masofa (km): "))
narx = 5000 + km * 2500
narx = math.ceil(narx / 1000) * 1000
print(f"To'lov: {narx} so'm")
```

```text
Masofa (km): 7.3
To'lov: 24000 so'm
```

|||

#### Endi o'zingiz davom ettiring

1. Kutish vaqtini so'rang: har daqiqasi 500 so'm.
2. 10% chegirma bilan narxni ham ko'rsating.
3. Narxni dollarda chiqaring (kurs 12750, 2 xona).
4. Hammasini chek ko'rinishida chiqaring.

---

###### 05 · Viktorina
## Kompyutersiz ayting: ekranda nima chiqadi?

### 1-savol

```python
print(abs(-7) + 3)
```

### 2-savol

```python
print(round(4.5))
```

### 3-savol

```python
import math
print(math.ceil(4.1))
```

### 4-savol

```python
print(max(3, 8, 1))
```

### 5-savol

```python
import math
print(math.sqrt(49))
```

### 6-savol

```python
print(int(-3.7))
```

---

###### 05 · Viktorina
## Javoblar: nechta to'g'ri topdingiz?

### 1-savol

`10`

`abs(-7)` — 7, keyin 7 + 3.

### 2-savol

`4`

Teng yarim — juft songa.

### 3-savol

`5`

`ceil` — doim yuqoriga.

### 4-savol

`8`

Eng kattasi — 8.

### 5-savol

`7.0`

`sqrt` doim float beradi.

### 6-savol

`-3`

`int()` kasrni kesadi.

---

###### Xulosa va uyga vazifa
## Bugun nimani o'rgandik

### Esda qoladigan 4 narsa {.sariq}

- `abs`, `round`, `min`, `max`, `sum`, `pow` — import shart emas
- `import math`: `sqrt`, `pi`, `ceil`, `floor`, `factorial`
- `round(2.5)` → 2: teng yarim juft songa
- `math.ceil` — yuqoriga, `math.floor` — pastga

|||

### Uyga vazifa {.qizil}

1. Aylana: uzunlik va yuza (r = 7)
2. Uchburchak: gipotenuza, perimetr, yuza
3. Narxni mingga yaxlitlash
4. Chegirma: 20%
5. Baholar: o'rtacha va yaxlitlash

Batafsil — platformadagi «Uy vazifasi» bo'limida.

::: ustozga

Dars rejasi (2 soat):
- 0–15 daq: 3-dars uy vazifasi (strip, title, f-string).
- 15–40 daq: tayyor funksiyalar (3–6-slaydlar). round(2.5) = 2 ni o'quvchilar avval taxmin qilsin, keyin tekshirsin — «bank usuli»ni tushuntiring.
- 40–50 daq: Amaliyot 1.
- 50–60 daq: math moduli (8–10-slaydlar). Yaxlitlash jadvalini doskada to'ldiring: o'quvchilar har katakni o'zi topsin.
- 60–70 daq: tanaffus.
- 70–90 daq: ildiz, 0.1 + 0.2 muammosi, hayotiy misollar (11–14-slaydlar).
- 90–110 daq: Amaliyot 2 va 3.
- 110–120 daq: viktorina, platformadagi test va uy vazifasi.

Ko'p uchraydigan xatolar: import math'ni unutish (NameError: name 'math' is not defined); sqrt'ni math. siz yozish; round(x, 2) o'rniga round(x) — kasr yo'qoladi; ceil va floor'ni adashtirish; manfiy sonlarda int() va floor() farqini bilmaslik.

::: test

? Quyidagi kod nima chiqaradi?
```python
import math
print(math.pi)
```
+ 3.141592653589793
- 3.14
- 22/7
- 3
> math.pi — π sonining aniq qiymati (15–16 xonagacha).

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(abs(-12))
```
= 12
> abs() — sonning musbat qiymati (moduli).

? Quyidagi kod nima chiqaradi?
```python
print(round(7.6))
```
+ 8
- 7
- 7.6
- 8.0
> round() eng yaqin butun songa yaxlitlaydi va int qaytaradi.

? Quyidagi kod nima chiqaradi?
```python
print(round(2.5))
```
+ 2
- 3
- 2.5
- 3.0
> Python teng yarimni juft songa yaxlitlaydi: round(2.5) = 2, round(3.5) = 4.

? Quyidagi kod nima chiqaradi?
```python
import math
print(math.sqrt(81))
```
+ 9.0
- 9
- 81
- 40.5
> math.sqrt doim float qaytaradi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(pow(3, 2))
```
= 9
> pow(3, 2) — 3 ning 2-darajasi.

? Quyidagi kod nima chiqaradi?
```python
import math
print(math.floor(-2.5))
```
+ -3
- -2
- -2.5
- 2
> floor — pastga (kichik tomonga) yaxlitlaydi: -2.5 dan pastdagi butun son — -3.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
import math
print(math.ceil(2.1))
```
= 3
> ceil — yuqoriga yaxlitlaydi.

? Quyidagi kod nima chiqaradi?
```python
print(max([4, 9, 2]))
```
+ 9
- 4
- 2
- [4, 9, 2]

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(sum([1, 2, 3, 4]))
```
= 10
> sum() ro'yxat elementlarini qo'shadi.

? Quyidagi kod nima chiqaradi?
```python
import math
print(math.factorial(4))
```
+ 24
- 16
- 10
- 4
> 4! = 1 * 2 * 3 * 4 = 24.

? Quyidagi kod nima chiqaradi?
```python
print(min(5, -1, 3))
```
+ -1
- 3
- 5
- 1

? math modulidan foydalanish uchun nima yoziladi?
+ import math
- include math
- using math
- math.import()

? Ifodani natijasi bilan moslang:
math.sqrt(25) :: 5.0
math.ceil(1.2) :: 2
math.floor(1.8) :: 1
abs(-7) :: 7

::: uy-vazifasi

5 ta topshiriq — hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying (yoki .py fayl biriktiring). Har topshiriq oldidan izoh yozing: # 1-topshiriq, # 2-topshiriq va h.k.
Kod boshida bir marta import math yozing.

1-topshiriq. Aylana
r = 7. math.pi bilan aylana uzunligi (2 * pi * r) va yuzasini (pi * r ** 2) hisoblang, 2 xonagacha yaxlitlang.

Kutilgan natija:
Uzunlik: 43.98
Yuza: 153.94

2-topshiriq. To'g'ri burchakli uchburchak
Katetlar a = 6, b = 8. Gipotenuzani math.sqrt bilan toping (c = √(a² + b²)), so'ng perimetr (a + b + c) va yuzani (a * b / 2) chiqaring.

Kutilgan natija:
Gipotenuza: 10.0
Perimetr: 24.0
Yuza: 24.0

3-topshiriq. Narxni yaxlitlash
narx = 36750. Narxni mingga yaxlitlang: yuqoriga (math.ceil), pastga (math.floor) va eng yaqiniga (round). Maslahat: avval 1000 ga bo'ling, keyin yana 1000 ga ko'paytiring.

Kutilgan natija:
Yuqoriga: 37000
Pastga: 36000
Eng yaqini: 37000

4-topshiriq. Chegirma
Telefon narxi 249000 so'm, chegirma 20%. Chegirma summasi va yangi narxni chiqaring (natijalar butun son bo'lsin).

Kutilgan natija:
Chegirma: 49800
Yangi narx: 199200

5-topshiriq. Baholar
baholar = [5, 3, 4, 5]. max, min, sum va len bilan eng yuqori, eng past, o'rtacha va yaxlitlangan o'rtacha bahoni chiqaring.

Kutilgan natija:
Eng yuqori: 5
Eng past: 3
O'rtacha: 4.25
Yaxlitlangan: 4
