+++
title = "2-mavzu: o'zgaruvchilar va ma'lumot turlari"
summary = "O'zgaruvchi, int/float/str/bool, type(), turni o'zgartirish va input()"
+++

::: slaydlar

###### Python darsi · 2-mavzu
# O'zgaruvchilar va turlar

Ma'lumotni saqlash, int, float, str, bool va input()

`ism = "Ali"` `yosh = 17` nazariya + 3 ta amaliyot + viktorina

---

###### Bugungi reja
## Darsda nimalarni o'rganamiz?

### 01 O'zgaruvchi

Nomli quti: qiymat berish va nomlash qoidalari

### 02 Turlar

`int`, `float`, `str`, `bool` va `type()`

### 03 Turni o'zgartirish

`int()`, `float()`, `str()` — qachon kerak

### 04 input()

Foydalanuvchidan ma'lumot so'rash

---

###### 01 · Muammo
## Ism o'zgarsa, hamma qatorni tuzatamizmi?

### Takrorlash {.qizil}

```python
print("Ali", "matematika", 5)
print("Ali", "fizika", 4)
print("Ali", "tarix", 5)
# ism o'zgarsa — 3 joyni tuzatamiz
```

|||

### O'zgaruvchi bilan {.sariq}

```python
ism = "Ali"
print(ism, "matematika", 5)
print(ism, "fizika", 4)
print(ism, "tarix", 5)
```

Ismni bitta joyda o'zgartirsak — hamma qator o'zgaradi.

---

###### 02 · O'zgaruvchi
## O'zgaruvchi — nomli quti

```python
ism = "Ali"
yosh = 17
print(ism, yosh)    # Ali 17

yosh = 18
print(ism, yosh)    # Ali 18
```

|||

### = — qiymat berish

O'ngdagi qiymat chapdagi nomga yoziladi

### Nom — yorliq

Qiymat kerak bo'lsa, nomini yozamiz

### Qayta yozish mumkin

Yangi qiymat eskisining o'rnini oladi

---

###### 02 · O'zgaruvchi
## Qiymat o'zgarishi mumkin

```python
ball = 10
ball = ball + 5
print(ball)    # 15
ball += 3
print(ball)    # 18
ball *= 2
print(ball)    # 36
```

|||

| Qisqa | To'liq |
|---|---|
| `x += 3` | `x = x + 3` |
| `x -= 2` | `x = x - 2` |
| `x *= 4` | `x = x * 4` |
| `x /= 2` | `x = x / 2` |

`ball = ball + 5` — «eski qiymatga 5 qo'sh va yana ball'ga yoz».

---

###### 02 · O'zgaruvchi
## Bir nechta qiymat birdan

#### Kod

```python
a, b = 2, 5
print(a * b)     # 10

a, b = b, a      # o'rin almashtirish
print(a, b)      # 5 2

x = y = 0
print(x, y)      # 0 0
```

|||

#### Esda tuting

Vergul bilan bir qatorda bir nechta o'zgaruvchiga qiymat beriladi.

`a, b = b, a` — ikki qiymatni almashtirishning eng qisqa yo'li.

---

###### 02 · O'zgaruvchi
## Nomlash qoidalari

### To'g'ri {.yashil}

```diff
+ yosh = 17
+ talaba_ismi = "Ali"
+ ball2 = 90
+ jami_narx = 25000
```

|||

### Noto'g'ri {.qizil}

```diff
- 2ball = 90         raqam bilan
- talaba ismi = 1    bo'sh joy
- if = 5             band so'z
```

`Yosh` va `yosh` — ikki xil nom. Nomni ma'noli qo'ying: `x` emas, `narx`.

---

###### 03 · Turlar
## To'rt asosiy tur

### int

Butun son: `17`, `-3`, `0`

### float

Kasr son: `3.14`, `2.0`, `-0.5`

### str

Matn: `"Salom"`, `'7'`

### bool

Mantiqiy: `True`, `False`

---

###### 03 · Turlar
## type() — turini bilish

#### Kod

```python
print(type(17))
print(type(3.5))
print(type("17"))
print(type(10 > 3))
```

|||

#### Ekranda

```text
<class 'int'>
<class 'float'>
<class 'str'>
<class 'bool'>
```

Qo'shtirnoqdagi `"17"` — son emas, matn!

---

###### Amaliyot 1 · 10 daqiqa
## Men haqimda

1. `ism`, `yosh`, `boy` (bo'y, metrda) va `talaba` o'zgaruvchilarini yarating.
2. Har birini va uning turini `type()` bilan chiqaring.
3. `yosh` ga 1 qo'shing (`+=`) va yangi qiymatni chiqaring.
4. `a = 3`, `b = 8` — yig'indi, ayirma, ko'paytma va bo'linmani chiqaring.

> **Yulduzli topshiriq:** kvadrat tomoni `a = 7`. Perimetr va yuzani «Perimetr: 28», «Yuza: 49» ko'rinishida chiqaring.

---

###### 04 · Turni o'zgartirish
# Matn + son = xato?

Turlar aralashsa, Python adashadi — biz unga yordam beramiz.

`int()` `float()` `str()`

---

###### 04 · Turni o'zgartirish
## Turni o'zgartiruvchi funksiyalar

| Funksiya | Misol | Natija |
|---|---|---|
| `int()` | `int("12") + 3` | `15` |
| `int()` | `int(7.9)` | `7` |
| `float()` | `float(3)` | `3.0` |
| `str()` | `str(10) * 2` | `'1010'` |
| matn + matn | `"12" + "3"` | `'123'` |

`int(7.9)` — **kesadi**, yaxlitlamaydi: natija 7, 8 emas.

---

###### 04 · Turni o'zgartirish
## Diqqat: matn + son

### Xato {.qizil}

```python
yosh = 17
print("Yosh: " + yosh)
```

```text
TypeError: can only concatenate
str (not "int") to str
```

|||

### To'g'ri {.yashil}

```python
yosh = 17
print("Yosh: " + str(yosh))
print("Yosh:", yosh)
```

`+` bilan faqat matnni matnga qo'shamiz. Vergul esa har qanday turni qabul qiladi.

---

###### 05 · input()
## input() — foydalanuvchidan so'rash

#### Kod

```python
ism = input("Ismingiz: ")
print("Salom,", ism)
```

|||

#### Ekranda

```text
Ismingiz: Madina
Salom, Madina
```

Dastur shu yerda to'xtaydi va foydalanuvchi yozib Enter bosishini kutadi.

---

###### 05 · input()
## input() doim matn qaytaradi

### Xato {.qizil}

```python
yil = input("Tug'ilgan yil: ")
print(2026 - yil)
```

```text
TypeError: unsupported operand type(s)
for -: 'int' and 'str'
```

|||

### To'g'ri {.yashil}

```python
yil = int(input("Tug'ilgan yil: "))
print(2026 - yil)
```

```text
Tug'ilgan yil: 2008
18
```

Hisoblash kerak bo'lsa — `int()` yoki `float()` bilan o'rang.

---

###### Amaliyot 2 · 10 daqiqa
## Yosh hisoblagich

1. Ism va tug'ilgan yilni `input()` bilan so'rang.
2. 2026-yilda necha yosh bo'lishini hisoblang (`int()` ni unutmang!).
3. «Ali, siz 2026-yilda 18 yoshdasiz» ko'rinishida chiqaring.
4. 10 yildan keyin necha yosh bo'lishini ham chiqaring.

> **Yulduzli topshiriq:** bo'yni metrda so'rang (`float`) va santimetrda chiqaring: 1.75 kiritilsa — 175.0.

---

###### Amaliyot 3 · Mini loyiha · 15 daqiqa
## Valyuta kalkulyatori

#### Kod

```python
kurs = 12750
som = int(input("Summa (so'm): "))
dollar = som / kurs
print("Dollar:", round(dollar, 2))
```

```text
Summa (so'm): 1000000
Dollar: 78.43
```

|||

#### Endi o'zingiz davom ettiring

1. Kursni ham `input()` bilan so'rang.
2. Teskari hisob: dollardan so'mga.
3. «1000000 so'm = 78.43 dollar» ko'rinishida chiqaring.
4. 1% xizmat haqini ayirib, qolganini ko'rsating.

`round(x, 2)` — sonni 2 xonagacha yaxlitlaydi.

---

###### 06 · Viktorina
## Kompyutersiz ayting: ekranda nima chiqadi?

### 1-savol

```python
x = 5
x = x + 2
print(x)
```

### 2-savol

```python
print(type(3.0))
```

### 3-savol

```python
print("5" + "5")
```

### 4-savol

```python
print(int("5") + 5)
```

### 5-savol

```python
a, b = 1, 2
a, b = b, a
print(a)
```

### 6-savol

```python
print(int(9.99))
```

---

###### 06 · Viktorina
## Javoblar: nechta to'g'ri topdingiz?

### 1-savol

`7`

Eski qiymat 5 ga 2 qo'shildi.

### 2-savol

`<class 'float'>`

Nuqtali son — float.

### 3-savol

`55`

Ikki matn yopishdi.

### 4-savol

`10`

`int("5")` — son 5.

### 5-savol

`2`

Qiymatlar o'rin almashdi.

### 6-savol

`9`

`int()` kasr qismini kesadi.

---

###### Xulosa va uyga vazifa
## Bugun nimani o'rgandik

### Esda qoladigan 4 narsa {.sariq}

- O'zgaruvchi — qiymatga berilgan nom: `ism = "Ali"`
- Turlar: `int`, `float`, `str`, `bool`; `type()` turini aytadi
- `int()`, `float()`, `str()` — turni o'zgartiradi
- `input()` doim **matn** qaytaradi

|||

### Uyga vazifa {.qizil}

1. Turlar: 4 ta o'zgaruvchi va `type()`
2. Yosh hisoblagich: `input()` bilan
3. Kvadrat: perimetr va yuza
4. Valyuta: so'mdan dollarga
5. O'rin almashtirish: bir qatorda

Batafsil — platformadagi «Uy vazifasi» bo'limida.

::: ustozga

Dars rejasi (2 soat):
- 0–15 daq: 1-dars uy vazifasini ko'rib chiqish (eng ko'p xato — qo'shtirnoq va qavs).
- 15–40 daq: o'zgaruvchi (3–7-slaydlar). Doskada «quti» rasmini chizing: nom — yorliq, qiymat — ichidagi narsa. `ball = ball + 5` ni bosqichma-bosqich tushuntiring.
- 40–50 daq: turlar va type() (8–9-slaydlar).
- 50–60 daq: Amaliyot 1.
- 60–70 daq: tanaffus.
- 70–90 daq: turni o'zgartirish va input() (11–15-slaydlar). "12" + "3" va 12 + 3 farqini o'quvchilar o'zi topib aytsin. int() unutilganda chiqadigan TypeError'ni birga o'qing.
- 90–110 daq: Amaliyot 2 va 3.
- 110–120 daq: viktorina, platformadagi test va uy vazifasi.

Ko'p uchraydigan xatolar: input() natijasini int() siz hisoblash; o'zgaruvchi nomida bo'sh joy yoki raqam bilan boshlash; = va == ni adashtirish (shartlar darsida yana keladi); o'zgaruvchini e'lon qilmasdan ishlatish (NameError); int(7.9) ni 8 deb o'ylash.

::: test

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
x = 5
x = x + 2
print(x)
```
= 7
> x ning yangi qiymati: 5 + 2 = 7.

? type("5") nima qaytaradi?
+ <class 'str'>
- <class 'int'>
- <class 'float'>
- <class 'char'>
> Qo'shtirnoq ichidagi qiymat — matn (str).

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(int("12") + 3)
```
= 15
> int("12") matnni songa aylantiradi: 12 + 3 = 15.

? Quyidagi kod nima chiqaradi?
```python
print("12" + "3")
```
+ 123
- 15
- 12 3
- Xato beradi
> Ikki matn qo'shilsa, ular yopishtiriladi.

? Quyidagi kod nima chiqaradi?
```python
print(int(7.9))
```
+ 7
- 8
- 7.9
- Xato beradi
> int() kasr qismini tashlab yuboradi (yaxlitlamaydi).

? Quyidagi kod nima chiqaradi?
```python
print(float(3))
```
+ 3.0
- 3
- 3.00
- "3.0"
> float() butun sonni haqiqiy songa aylantiradi.

? Quyidagi kod nima chiqaradi?
```python
print(str(10) * 2)
```
+ 1010
- 20
- 10 10
- Xato beradi
> str(10) — matn "10", matn 2 marta takrorlanadi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
a, b = 2, 5
print(a * b)
```
= 10
> Bir qatorda ikki o'zgaruvchi: a = 2, b = 5.

? Qaysi qiymat bool turida?
+ True
- "True"
- 1
- "False"
> Qo'shtirnoqdagi "True" — matn, 1 — butun son.

? Quyidagi kod nima chiqaradi?
```python
print(type(10 > 3))
```
+ <class 'bool'>
- <class 'int'>
- <class 'str'>
- True
> Taqqoslash natijasi — True yoki False, ya'ni bool.

? ism va Ism — bitta o'zgaruvchimi?
+ Yo'q, Python katta-kichik harfni farqlaydi — bular ikki xil o'zgaruvchi
- Ha, bitta o'zgaruvchi
- Faqat funksiyalarda farq qiladi
- Xato beradi
> Python katta va kichik harflarni farqlaydi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
x = 4
x *= 3
print(x)
```
= 12
> x *= 3 — bu x = x * 3 degani.

? Funksiyani natijasi bilan moslang:
int("8") :: 8
float("2.5") :: 2.5
str(3) :: "3"
bool("") :: False
> Bo'sh matn bool'da False, bo'sh bo'lmagani — True.

? None qiymati nimani bildiradi?
+ Qiymat yo'qligini
- Nol sonini
- Bo'sh matnni
- Xatoni

::: uy-vazifasi

5 ta topshiriq — hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying (yoki .py fayl biriktiring). Har topshiriq oldidan izoh yozing: # 1-topshiriq, # 2-topshiriq va h.k.
input() bilan ishlaydigan topshiriqlarda misoldagi qiymatni kiritib tekshiring.

1-topshiriq. Turlar
To'rtta o'zgaruvchi yarating: ism = "Ali", yosh = 17, boy = 1.75, talaba = True. Har birini va uning turini (type) bitta qatorda chiqaring.

Kutilgan natija:
Ali <class 'str'>
17 <class 'int'>
1.75 <class 'float'>
True <class 'bool'>

2-topshiriq. Yosh hisoblagich
Tug'ilgan yilni input() bilan so'rang va 2026-yilda necha yosh bo'lishini chiqaring.

Kutilgan natija (2008 kiritilsa):
Siz 2026-yilda 18 yoshdasiz

3-topshiriq. Kvadrat
Kvadrat tomonini input() bilan so'rang (butun son). Perimetr (4 * a) va yuzani (a * a) chiqaring.

Kutilgan natija (5 kiritilsa):
Perimetr: 20
Yuza: 25

4-topshiriq. Valyuta
1 dollar = 12750 so'm deb oling. So'mdagi summani input() bilan so'rang va dollardagi qiymatini 2 xonagacha yaxlitlab chiqaring (round).

Kutilgan natija (1000000 kiritilsa):
78.43 dollar

5-topshiriq. O'rin almashtirish
a = "olma", b = "anor". Bitta qatorda a va b qiymatlarini almashtiring, so'ng print(a, b).

Kutilgan natija:
anor olma
