+++
title = "8-mavzu: for sikli va range()"
summary = "for bilan ro'yxat, matn va sonlar ustida yurish, range(), yig'indi va sanash andozalari"
+++

::: slaydlar

###### Python darsi · 8-mavzu
# for sikli va range()

Bir ishni ko'p marta bajarish: ro'yxat, matn va sonlar ustida yurish

`for i in range(5):` `for ism in dostlar:` nazariya + 3 ta amaliyot + viktorina

---

###### Bugungi reja
## Darsda nimalarni o'rganamiz?

### 01 for

Ro'yxat va matnning har bir elementi uchun

### 02 range()

Sonlar ketma-ketligi: boshi, oxiri, qadam

### 03 Hisoblagich

Yig'indi, sanash, eng kattasini topish

### 04 enumerate

Element va uning tartib raqami

---

###### 01 · Muammo
## 100 marta print yozamizmi?

### Takrorlash {.qizil}

```python
print("1-o'quvchi: tayyor")
print("2-o'quvchi: tayyor")
print("3-o'quvchi: tayyor")
# ... yana 97 qator
```

|||

### Sikl bilan {.sariq}

```python
for i in range(1, 101):
    print(f"{i}-o'quvchi: tayyor")
```

2 qator — 100 ta natija. Son o'zgarsa, faqat `range` o'zgaradi.

---

###### 02 · for
## for — har bir element uchun

#### Kod

```python
dostlar = ["Ali", "Laylo", "Sardor"]

for ism in dostlar:
    print("Salom,", ism)
```

|||

#### Ekranda

```text
Salom, Ali
Salom, Laylo
Salom, Sardor
```

`ism` har aylanishda navbatdagi elementni oladi. Ikki nuqta va indent — xuddi `if` dagidek.

---

###### 02 · for
## Matn ustida yurish

### Har bir harf

```python
for harf in "Salom":
    print(harf, end=" ")
```

```text
S a l o m
```

|||

### Unlilarni sanash

```python
soz = "Navoiy"
unli = 0
for h in soz.lower():
    if h in "aeiou":
        unli += 1
print(unli)    # 3
```

---

###### 03 · range()
## range() — sonlar ketma-ketligi

| Misol | Natija |
|---|---|
| `list(range(5))` | `[0, 1, 2, 3, 4]` |
| `list(range(1, 6))` | `[1, 2, 3, 4, 5]` |
| `list(range(0, 11, 2))` | `[0, 2, 4, 6, 8, 10]` |
| `list(range(5, 0, -1))` | `[5, 4, 3, 2, 1]` |

Oxiri **kirmaydi** — kesishdagidek. Uchinchi son — qadam (manfiy bo'lsa, teskari sanaydi).

---

###### 03 · range()
## for va range() birga

#### Kod

```python
for i in range(1, 6):
    print(i, "x", i, "=", i * i)
```

|||

#### Ekranda

```text
1 x 1 = 1
2 x 2 = 4
3 x 3 = 9
4 x 4 = 16
5 x 5 = 25
```

Ko'paytirish jadvali, kvadratlar, sanoq — hammasi shu andoza bilan.

---

###### Amaliyot 1 · 10 daqiqa
## Sanoq va jadval

1. 1 dan 10 gacha sonlarni chiqaring.
2. 10 dan 1 gacha teskari sanang (`range(10, 0, -1)`).
3. 7 ning ko'paytirish jadvalini chiqaring: «7 x 1 = 7» va hokazo.
4. Ismingizning har bir harfini alohida qatorda chiqaring.

> **Yulduzli topshiriq:** 1 dan 50 gacha 3 ga bo'linadigan sonlarni bitta qatorda chiqaring (`end=" "`).

---

###### 04 · Hisoblagich
# Sikl ichida hisoblaymiz

Yig'indi, sanoq, eng kattasi — uchala andoza bir xil.

`jami += x` `soni += 1`

---

###### 04 · Hisoblagich
## Yig'indi andozasi

```python
narxlar = [12000, 4000, 9000, 15000]
jami = 0
for narx in narxlar:
    jami += narx
print(jami)            # 40000
print(sum(narxlar))    # 40000
```

|||

### 1. Boshlang'ich qiymat

`jami = 0` — sikldan **oldin**

### 2. Sikl ichida

`jami += narx` — har aylanishda qo'shamiz

### 3. Natija

Sikldan keyin — indentsiz `print`

---

###### 04 · Hisoblagich
## Sanash va saralab olish

### Shart bilan sanash

```python
baholar = [5, 3, 4, 5, 2, 5]
besh = 0
for b in baholar:
    if b == 5:
        besh += 1
print(besh)    # 3
```

|||

### Yangi ro'yxat yig'ish

```python
sonlar = [3, 8, 11, 6, 7]
juftlar = []
for s in sonlar:
    if s % 2 == 0:
        juftlar.append(s)
print(juftlar)    # [8, 6]
```

---

###### 04 · Hisoblagich
## Eng kattasini o'zimiz topamiz

```python
sonlar = [14, 27, 9, 31, 22]
eng = sonlar[0]
for s in sonlar:
    if s > eng:
        eng = s
print(eng)    # 31
```

|||

### Andoza

Birinchisini «eng katta» deb olamiz, keyin har birini u bilan solishtiramiz.

### max() ham shunday ishlaydi

Algoritmni bilish — dasturchi uchun muhim: intervyularda ko'p so'raladi.

---

###### 04 · Hisoblagich
## enumerate — tartib raqami bilan

#### Kod

```python
mevalar = ["olma", "anor", "nok"]
for i, meva in enumerate(mevalar, 1):
    print(f"{i}. {meva}")
```

|||

#### Ekranda

```text
1. olma
2. anor
3. nok
```

`enumerate(royxat, 1)` — tartib raqami 1 dan boshlanadi.

---

###### 04 · Hisoblagich
## Yangi boshlovchilarning 4 xatosi

### 1. Ikki nuqta yo'q

```diff
- for i in range(5)      SyntaxError
+ for i in range(5):
```

### 2. Hisoblagich sikl ichida

```diff
- for x in a:
-     jami = 0           har safar 0!
+ jami = 0
+ for x in a:
```

### 3. range oxiri kirmaydi

```diff
- range(1, 10)           1 … 9
+ range(1, 11)           1 … 10
```

### 4. print sikl ichida

```diff
-     print(jami)        har aylanishda
+ print(jami)            bir marta
```

---

###### Amaliyot 2 · 10 daqiqa
## Hafta haroratlari

1. `harorat = [18, 21, 25, 19, 23, 27, 22]` ro'yxatini yarating.
2. O'rtacha haroratni sikl bilan hisoblang (`sum` siz).
3. 22 dan issiq kunlar sonini sanang.
4. Eng sovuq kunni `min` siz toping.

> **Yulduzli topshiriq:** eng issiq kun haftaning nechanchi kuni ekanini chiqaring (`enumerate`).

---

###### Amaliyot 3 · Mini loyiha · 15 daqiqa
## Savat cheki

#### Kod

```python
savat = [("non", 2, 4000), ("sut", 1, 12000),
         ("olma", 3, 5000)]
jami = 0
for nom, soni, narx in savat:
    summa = soni * narx
    print(f"{nom:6} {soni} x {narx} = {summa}")
    jami += summa
print("Jami:", jami, "so'm")
```

|||

#### Ekranda

```text
non    2 x 4000 = 8000
sut    1 x 12000 = 12000
olma   3 x 5000 = 15000
Jami: 35000 so'm
```

#### Endi o'zingiz davom ettiring

1. Savatga yana 2 ta mahsulot qo'shing.
2. 100 000 dan oshsa — 5% chegirma.
3. Eng qimmat xaridni toping.

---

###### 05 · Viktorina
## Kompyutersiz ayting: ekranda nima chiqadi?

### 1-savol

```python
for i in range(3):
    print(i, end=" ")
```

### 2-savol

```python
print(list(range(2, 8, 2)))
```

### 3-savol

```python
s = 0
for x in [1, 2, 3]:
    s += x
print(s)
```

### 4-savol

```python
n = 0
for h in "olma":
    n += 1
print(n)
```

### 5-savol

```python
print(len(range(10)))
```

### 6-savol

```python
a = []
for i in range(3):
    a.append(i * 2)
print(a)
```

---

###### 05 · Viktorina
## Javoblar: nechta to'g'ri topdingiz?

### 1-savol

`0 1 2`

`range(3)` — 0 dan, 3 kirmaydi.

### 2-savol

`[2, 4, 6]`

2 dan 2 qadam bilan, 8 kirmaydi.

### 3-savol

`6`

1 + 2 + 3.

### 4-savol

`4`

"olma" da 4 ta harf.

### 5-savol

`10`

0 dan 9 gacha — 10 ta son.

### 6-savol

`[0, 2, 4]`

0·2, 1·2, 2·2.

---

###### Xulosa va uyga vazifa
## Bugun nimani o'rgandik

### Esda qoladigan 4 narsa {.sariq}

- `for x in royxat:` — har bir element uchun
- `range(boshi, oxiri, qadam)` — oxiri kirmaydi
- Hisoblagich sikldan **oldin**: `jami = 0`
- `enumerate(royxat, 1)` — tartib raqami bilan

|||

### Uyga vazifa {.qizil}

1. 1 dan 10 gacha kvadratlar
2. Juft sonlar yig'indisi (1–100)
3. 9 ning ko'paytirish jadvali
4. Gapdagi unlilar soni
5. Baholar statistikasi

Batafsil — platformadagi «Uy vazifasi» bo'limida.

::: ustozga

Dars rejasi (2 soat):
- 0–15 daq: 7-dars uy vazifasi (dict va set).
- 15–35 daq: for (3–5-slaydlar). Doskada jadval chizing: aylanish raqami, o'zgaruvchi qiymati, ekrandagi natija — o'quvchilar har aylanishni qo'lda kuzatsin.
- 35–50 daq: range() (6–7-slaydlar). range(1, 6) da 6 kirmasligini kesish bilan bog'lang.
- 50–60 daq: Amaliyot 1.
- 60–70 daq: tanaffus.
- 70–90 daq: hisoblagich andozalari va enumerate (9–13-slaydlar). Har andozani 3 qadam bilan yodlating: oldin, ichida, keyin.
- 90–110 daq: Amaliyot 2 va 3.
- 110–120 daq: viktorina, platformadagi test va uy vazifasi.

Ko'p uchraydigan xatolar: jami = 0 ni sikl ichiga yozish; print(jami) ni sikl ichida qoldirish (har aylanishda chiqadi); range(1, 10) da 10 kiradi deb o'ylash; ikki nuqta va indentni unutish; sikl o'zgaruvchisi nomini sikldan keyin ham ishlatib, oxirgi qiymat qolishini bilmaslik.

::: test

? Quyidagi kod nima chiqaradi?
```python
for i in range(3):
    print(i, end=" ")
```
+ 0 1 2
- 1 2 3
- 0 1 2 3
- 3
> range(3) — 0 dan boshlanadi, 3 kirmaydi.

? Quyidagi kod nima chiqaradi?
```python
print(list(range(1, 6)))
```
+ [1, 2, 3, 4, 5]
- [1, 2, 3, 4, 5, 6]
- [0, 1, 2, 3, 4, 5]
- [2, 3, 4, 5, 6]
> range(1, 6): 1 dan 5 gacha, oxiri kirmaydi.

? Quyidagi kod nima chiqaradi?
```python
print(list(range(0, 10, 3)))
```
+ [0, 3, 6, 9]
- [0, 3, 6]
- [3, 6, 9]
- [0, 3, 6, 9, 12]
> Uchinchi son — qadam: 0, 3, 6, 9; 12 esa 10 dan katta.

? Quyidagi kod nima chiqaradi?
```python
print(list(range(5, 0, -1)))
```
+ [5, 4, 3, 2, 1]
- [5, 4, 3, 2, 1, 0]
- [1, 2, 3, 4, 5]
- []
> Manfiy qadam — teskari sanaydi; 0 kirmaydi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
s = 0
for x in [2, 4, 6]:
    s += x
print(s)
```
= 12
> 2 + 4 + 6 = 12.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
n = 0
for h in "dastur":
    n += 1
print(n)
```
= 6
> Har bir harf uchun n bittaga oshadi: "dastur" da 6 ta harf.

? Quyidagi kod nima chiqaradi?
```python
for h in "abc":
    print(h.upper(), end="")
```
+ ABC
- abc
- A B C
- Xato beradi
> end="" — harflar orasiga hech narsa qo'yilmaydi.

? Quyidagi kod nima chiqaradi?
```python
a = []
for i in range(4):
    a.append(i * i)
print(a)
```
+ [0, 1, 4, 9]
- [1, 4, 9, 16]
- [0, 2, 4, 6]
- [0, 1, 4, 9, 16]
> i: 0, 1, 2, 3 — kvadratlari 0, 1, 4, 9.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
k = 0
for b in [5, 3, 5, 4, 5]:
    if b == 5:
        k += 1
print(k)
```
= 3
> Faqat 5 ga teng baholar sanaladi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
eng = 0
for x in [7, 2, 9, 4]:
    if x > eng:
        eng = x
print(eng)
```
= 9
> Eng katta qiymat har safar yangilanadi: 7, keyin 9.

? enumerate(royxat, 1) nima beradi?
+ Har bir element va uning 1 dan boshlanadigan tartib raqami
- Faqat elementlar
- Ro'yxat uzunligi
- Faqat indekslar
> for i, x in enumerate(royxat, 1) — i: 1, 2, 3...

? Yig'indi hisoblashda jami = 0 qayerda yozilishi kerak?
+ Sikldan oldin
- Sikl ichida
- Sikldan keyin
- Farqi yo'q
> Sikl ichida yozilsa, har aylanishda 0 bo'lib qoladi.

? 1 dan 5 gacha sonlar yig'indisini hisoblaydigan kod qatorlarini tartibga qo'ying.
1. jami = 0
2. for i in range(1, 6):
3. jami += i
4. print(jami)

? range ifodasini sonlar bilan moslang:
range(3) :: 0, 1, 2
range(1, 4) :: 1, 2, 3
range(0, 6, 2) :: 0, 2, 4
range(3, 0, -1) :: 3, 2, 1

::: uy-vazifasi

5 ta topshiriq — hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying (yoki .py fayl biriktiring). Har topshiriq oldidan izoh yozing: # 1-topshiriq, # 2-topshiriq va h.k.
Hamma topshiriqda for siklidan foydalaning. Javobni qo'lda yozmang — hisoblashni kod qilsin.

1-topshiriq. Kvadratlar
1 dan 10 gacha sonlarning kvadratlarini bitta qatorda chiqaring (print(..., end=" ")).

Kutilgan natija:
1 4 9 16 25 36 49 64 81 100

2-topshiriq. Juft sonlar yig'indisi
1 dan 100 gacha juft sonlar yig'indisini sikl bilan hisoblang (sum() ishlatmang).

Kutilgan natija:
2550

3-topshiriq. Ko'paytirish jadvali
9 ning ko'paytirish jadvalini chiqaring (1 dan 10 gacha).

Kutilgan natija:
9 x 1 = 9
9 x 2 = 18
9 x 3 = 27
9 x 4 = 36
9 x 5 = 45
9 x 6 = 54
9 x 7 = 63
9 x 8 = 72
9 x 9 = 81
9 x 10 = 90

4-topshiriq. Unlilar
matn = "Men Python dasturlashni o'rganyapman". Unli harflar (a, e, i, o, u) sonini sanang; katta harflar ham hisoblansin (lower()).

Kutilgan natija:
Unlilar soni: 10

5-topshiriq. Baholar statistikasi
baholar = [5, 3, 4, 5, 2, 5, 4]. Sikl bilan 5 lar sonini va yig'indini hisoblang (count va sum ishlatmang), so'ng o'rtachani chiqaring.

Kutilgan natija:
5 lar soni: 3
Yig'indi: 28
O'rtacha: 4.0
