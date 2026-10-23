+++
title = "9-mavzu: while sikli, break va continue"
summary = "Shart bajarilguncha takrorlash, while True va break, continue, random va «Son top» o'yini"
+++

::: slaydlar

###### Python darsi · 9-mavzu
# while, break, continue

Shart bajarilguncha takrorlash va «Son top» o'yini

`while x > 0:` `break` nazariya + 3 ta amaliyot + viktorina

---

###### Bugungi reja
## Darsda nimalarni o'rganamiz?

### 01 while

Shart rost ekan — takrorlash

### 02 break

`while True` va siklni to'xtatish

### 03 continue

Bitta qadamni o'tkazib yuborish

### 04 O'yin

`random` va «Son top» o'yini

---

###### 01 · Muammo
## Parolni necha marta so'raymiz?

### for bilan {.qizil}

```python
for i in range(3):
    parol = input("Parol: ")
# 3 marta so'radi —
# birinchisida to'g'ri yozsa ham!
```

|||

### while bilan {.sariq}

```python
parol = ""
while parol != "1234":
    parol = input("Parol: ")
print("Kirdingiz!")
```

`while` — necha marta kerakligi oldindan noma'lum bo'lsa.

---

###### 02 · while
## while — shart rost ekan

#### Kod

```python
n = 1
while n <= 5:
    print(n)
    n += 1
print("Tamom")
```

|||

#### Ekranda

```text
1
2
3
4
5
Tamom
```

Shart har aylanishdan **oldin** tekshiriladi. `n += 1` ni unutsangiz — sikl hech qachon tugamaydi!

---

###### 02 · while
## for yoki while?

| | for | while |
|---|---|---|
| Qachon | Necha marta — ma'lum | Shart bajarilguncha |
| Misollar | Ro'yxat, `range(10)` | Parol, o'yin, menyu |
| To'xtashi | O'zi tugaydi | Shart yolg'on bo'lganda |
| Xavf | Kam | Cheksiz sikl |

`for` — «har bir element uchun», `while` — «… bo'lguncha».

---

###### 02 · while
## Hayotiy misol: omonat

#### Kod

```python
pul = 1000000
yil = 0
while pul < 3000000:
    pul = pul * 125 // 100
    yil += 1
print(yil, "yilda:", pul, "so'm")
```

|||

#### Ekranda

```text
5 yilda: 3051757 so'm
```

Yiliga 25% foiz bilan pul necha yilda 3 baravar bo'ladi? Necha yil — oldindan noma'lum, shuning uchun `while`.

---

###### Amaliyot 1 · 10 daqiqa
## while bilan mashq

1. 1 dan 20 gacha toq sonlarni `while` bilan chiqaring.
2. Foydalanuvchi 0 kiritguncha sonlarni so'rang va yig'indisini chiqaring.
3. 2 ning darajalarini 1000 dan oshguncha chiqaring: 1 2 4 8 …
4. Sonda nechta raqam borligini toping: 50317 → 5 (`// 10`).

> **Yulduzli topshiriq:** parolni 3 marta xato kiritsa — «Bloklandi», to'g'ri bo'lsa — «Xush kelibsiz».

---

###### 03 · break va continue
# Siklni boshqaramiz

To'xtatish yoki qadamni o'tkazib yuborish.

`break` `continue` `while True:`

---

###### 03 · break va continue
## while True va break

#### Kod

```python
while True:
    soz = input("So'z (chiqish: q): ")
    if soz == "q":
        break
    print(soz.upper())
print("Xayr!")
```

|||

#### Ekranda

```text
So'z (chiqish: q): salom
SALOM
So'z (chiqish: q): q
Xayr!
```

`break` — siklni darhol to'xtatadi. `while True` — cheksiz sikl, undan faqat `break` bilan chiqiladi.

---

###### 03 · break va continue
## continue — qadamni o'tkazib yuborish

#### Kod

```python
for i in range(1, 8):
    if i % 3 == 0:
        continue
    print(i, end=" ")
```

```text
1 2 4 5 7
```

|||

### continue

Qolgan qatorlar o'tkazib yuboriladi, sikl keyingi aylanishdan davom etadi.

### break

Sikl butunlay to'xtaydi.

---

###### 03 · break va continue
## Qidiruv: topilsa — to'xtaymiz

#### Kod

```python
sonlar = [4, 9, 15, 22, 31]
for s in sonlar:
    if s > 10:
        print("Birinchi 10 dan kattasi:", s)
        break
```

|||

#### Ekranda

```text
Birinchi 10 dan kattasi: 15
```

Topildi — qolganlarini tekshirishga hojat yo'q. `break` vaqtni tejaydi.

---

###### 03 · break va continue
## Yangi boshlovchilarning 4 xatosi

### 1. O'zgaruvchi o'zgarmaydi

```diff
- while n <= 5:
-     print(n)           cheksiz!
+     n += 1
```

### 2. Sikldan oldin qiymat yo'q

```diff
- while javob != "ha":   NameError
+ javob = ""
```

### 3. break sikl tashqarisida

```diff
- if x > 5: break        SyntaxError
+ while True:
+     if x > 5: break
```

### 4. Shartda bitta =

```diff
- while x = 0:           SyntaxError
+ while x == 0:
```

---

###### 04 · O'yin
## random — tasodif moduli

```python
import random
# 1 dan 6 gacha tasodifiy son (zar)
print(random.randint(1, 6))
# ro'yxatdan tasodifiy element
print(random.choice(["tosh", "qaychi", "qog'oz"]))
```

|||

### randint(a, b)

a va b ham kiradi

### choice(royxat)

Ro'yxatdan tasodifiy element

### Har safar boshqacha

Shuning uchun o'yinlarda ishlatiladi

---

###### Amaliyot 2 · 10 daqiqa
## Zar va savollar

1. «Davom etamizmi? (ha/yo'q)» — «yo'q» deyilguncha so'rang.
2. Har aylanishda hisoblagichni oshiring va oxirida chiqaring.
3. Bo'sh javob kiritilsa — `continue` bilan qayta so'rang.
4. Zar tashlang (`random.randint(1, 6)`) — 6 tushguncha; necha marta tashlandi?

> **Yulduzli topshiriq:** «Tosh, qaychi, qog'oz» — kompyuter `random.choice` bilan tanlaydi, 3 raund o'ynang.

---

###### Amaliyot 3 · Mini loyiha · 15 daqiqa
## «Son top» o'yini

#### Kod

```python
import random
son = random.randint(1, 100)
urinish = 0
while True:
    taxmin = int(input("Taxmin: "))
    urinish += 1
    if taxmin < son:
        print("Kattaroq")
    elif taxmin > son:
        print("Kichikroq")
    else:
        print(f"Topdingiz! {urinish} urinishda")
        break
```

|||

#### Endi o'zingiz davom ettiring

1. 7 urinish chegarasi qo'ying.
2. Yutqazsa, sonni ko'rsating.
3. «Yana o'ynaymizmi?» — tashqi `while`.
4. Eng yaxshi natijani eslab qoling.

---

###### 05 · Viktorina
## Kompyutersiz ayting: ekranda nima chiqadi?

### 1-savol

```python
n = 3
while n > 0:
    print(n, end=" ")
    n -= 1
```

### 2-savol

```python
i = 0
while i < 10:
    i += 3
print(i)
```

### 3-savol

```python
for i in range(10):
    if i == 4:
        break
print(i)
```

### 4-savol

```python
s = 0
for i in range(5):
    if i == 2:
        continue
    s += i
print(s)
```

### 5-savol

```python
x = 100
while x > 10:
    x //= 2
print(x)
```

### 6-savol

```python
k = 0
while True:
    k += 1
    if k == 3:
        break
print(k)
```

---

###### 05 · Viktorina
## Javoblar: nechta to'g'ri topdingiz?

### 1-savol

`3 2 1`

n = 0 bo'lganda shart yolg'on.

### 2-savol

`12`

0 → 3 → 6 → 9 → 12.

### 3-savol

`4`

break — i shu qiymatda qoladi.

### 4-savol

`8`

0 + 1 + 3 + 4: ikkinchisi o'tkazildi.

### 5-savol

`6`

100 → 50 → 25 → 12 → 6.

### 6-savol

`3`

k = 3 da break.

---

###### Xulosa va uyga vazifa
## Bugun nimani o'rgandik

### Esda qoladigan 4 narsa {.sariq}

- `while shart:` — shart rost ekan takrorlaydi
- Shartdagi o'zgaruvchi sikl ichida o'zgarsin
- `break` — to'xtatadi, `continue` — keyingi qadamga
- `while True` + `break` — menyu va o'yinlar uchun

|||

### Uyga vazifa {.qizil}

1. Teskari sanoq va «Start!»
2. Raqamlar yig'indisi
3. Sonni teskari aylantirish
4. Omonat: necha yilda 2 baravar
5. Tub son: `break` bilan

Batafsil — platformadagi «Uy vazifasi» bo'limida.

::: ustozga

Dars rejasi (2 soat):
- 0–15 daq: 8-dars uy vazifasi (for va range).
- 15–35 daq: while (3–6-slaydlar). Cheksiz sikl nima ekanini xavfsiz ko'rsating va to'xtatish usulini o'rgating: terminalda Ctrl+C.
- 35–45 daq: Amaliyot 1.
- 45–60 daq: break va continue (8–11-slaydlar). Doskada jadval: aylanish, shart, nima bajarildi.
- 60–70 daq: tanaffus.
- 70–85 daq: random va Amaliyot 2.
- 85–110 daq: «Son top» o'yini (Amaliyot 3) — o'quvchilar juft bo'lib o'ynab ko'rsin, eng kam urinishda topgan g'olib.
- 110–120 daq: viktorina, platformadagi test va uy vazifasi.

Ko'p uchraydigan xatolar: sikl o'zgaruvchisini oshirishni unutish (cheksiz sikl); while shartidagi o'zgaruvchini sikldan oldin yaratmaslik; break'ni sikl tashqarisida yozish; continue'dan keyin hisoblagich oshmay qolishi (while ichida continue — yana cheksiz sikl xavfi); input() natijasini int() siz taqqoslash.

::: test

? Quyidagi kod nima chiqaradi?
```python
n = 3
while n > 0:
    print(n, end=" ")
    n -= 1
```
+ 3 2 1
- 3 2 1 0
- 1 2 3
- Cheksiz sikl bo'ladi
> n = 0 bo'lganda shart yolg'on — sikl tugaydi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
i = 1
while i < 20:
    i *= 2
print(i)
```
= 32
> 1 → 2 → 4 → 8 → 16 → 32: 32 < 20 yolg'on.

? while sikli qachon to'xtaydi?
+ Shart yolg'on bo'lganda
- Shart rost bo'lganda
- 10 marta aylangandan keyin
- Hech qachon
> while — shart rost ekan ishlaydi.

? Quyidagi kod nima chiqaradi?
```python
for i in range(1, 10):
    if i == 5:
        break
    print(i, end="")
```
+ 1234
- 12345
- 123456789
- 5
> i = 5 bo'lganda sikl to'xtaydi, 5 chiqmaydi.

? Quyidagi kod nima chiqaradi?
```python
for i in range(1, 6):
    if i == 3:
        continue
    print(i, end="")
```
+ 1245
- 12345
- 12
- 345
> continue — faqat 3 o'tkazib yuboriladi.

? Quyidagi kodda nima bo'ladi?
```python
n = 1
while n < 5:
    print(n)
```
+ Cheksiz sikl: n o'zgarmaydi
- 1 2 3 4 chiqadi
- Xato beradi
- Hech narsa chiqmaydi
> n doim 1 — shart hech qachon yolg'on bo'lmaydi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
x = 50
while x > 5:
    x = x // 2
print(x)
```
= 3
> 50 → 25 → 12 → 6 → 3.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
s = 0
n = 1
while n <= 4:
    s += n
    n += 1
print(s)
```
= 10
> 1 + 2 + 3 + 4 = 10.

? break nima qiladi?
+ Siklni darhol to'xtatadi
- Keyingi aylanishga o'tadi
- Dasturni butunlay yopadi
- Shartni qayta tekshiradi
> break — sikldan chiqish.

? continue nima qiladi?
+ Qolgan qatorlarni o'tkazib, keyingi aylanishga o'tadi
- Siklni to'xtatadi
- Siklni boshidan boshlaydi
- Hech narsa qilmaydi
> continue — faqat joriy aylanishni tugatadi.

? Quyidagi kod nima chiqaradi?
```python
import random
x = random.randint(1, 3)
print(x in [1, 2, 3])
```
+ True
- False
- 1
- Har safar boshqacha
> randint(1, 3) doim 1, 2 yoki 3 qaytaradi — chegaralar ham kiradi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
k = 0
while True:
    k += 2
    if k > 5:
        break
print(k)
```
= 6
> 2 → 4 → 6: 6 > 5 — break.

? «Son top» o'yini qatorlarini tartibga qo'ying.
1. import random
2. son = random.randint(1, 10)
3. while True:
4. taxmin = int(input("Taxmin: "))
5. if taxmin == son: break

? Kalit so'zni vazifasi bilan moslang:
while :: shart rost ekan takrorlaydi
break :: siklni to'xtatadi
continue :: keyingi aylanishga o'tadi
random.randint :: tasodifiy butun son beradi

::: uy-vazifasi

5 ta topshiriq — hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying (yoki .py fayl biriktiring). Har topshiriq oldidan izoh yozing: # 1-topshiriq, # 2-topshiriq va h.k.
Hamma topshiriqda while siklidan foydalaning.

1-topshiriq. Teskari sanoq
while bilan 10 dan 1 gacha bitta qatorda sanang, keyingi qatorda «Start!» deb chiqaring.

Kutilgan natija:
10 9 8 7 6 5 4 3 2 1
Start!

2-topshiriq. Raqamlar yig'indisi
son = 98765. while, % 10 va // 10 bilan raqamlari yig'indisini toping.

Kutilgan natija:
35

3-topshiriq. Teskari son
son = 2026. while bilan raqamlarini teskari tartibda yig'ib, yangi son hosil qiling (str() va [::-1] ishlatmang).

Kutilgan natija:
6202

4-topshiriq. Omonat
Bankka 1 000 000 so'm qo'yildi, har yili 20% qo'shiladi (pul = pul * 120 // 100). Necha yilda 2 000 000 dan oshadi?

Kutilgan natija:
4 yilda: 2073600 so'm

5-topshiriq. Tub son
son = 97. 2 dan son - 1 gacha bo'luvchi qidiring: topilsa — break. Natijani chiqaring.

Kutilgan natija:
97 — tub son
