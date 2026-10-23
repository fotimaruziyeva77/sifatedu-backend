+++
title = "10-mavzu: funksiyalar"
summary = "def, parametrlar, return, standart qiymatlar, nomli argumentlar va o'zgaruvchilar ko'rinishi"
+++

::: slaydlar

###### Python darsi · 10-mavzu
# Funksiyalar

def, parametrlar, return va standart qiymatlar

`def salom(ism):` `return x * 2` nazariya + 3 ta amaliyot + viktorina

---

###### Bugungi reja
## Darsda nimalarni o'rganamiz?

### 01 def

O'z buyrug'imizni yaratish va chaqirish

### 02 Parametrlar

Funksiyaga ma'lumot berish

### 03 return

Natijani qaytarish va ishlatish

### 04 Ko'rinish

Standart qiymat, mahalliy va global o'zgaruvchi

---

###### 01 · Muammo
## Bitta kodni 10 joyga nusxalaymizmi?

### Nusxalash {.qizil}

```python
print("*" * 20)
print("Ali — 95 ball")
print("*" * 20)
print("Vali — 78 ball")
print("*" * 20)
# uzunlik o'zgarsa — hammasini tuzatamiz
```

|||

### Funksiya bilan {.sariq}

```python
def chiziq():
    print("*" * 20)

chiziq()
print("Ali — 95 ball")
chiziq()
```

Bir marta yozamiz — istalgancha chaqiramiz.

---

###### 02 · def
## Funksiya yaratish va chaqirish

#### Kod

```python
def salomlash():
    print("Assalomu alaykum!")
    print("Darsga xush kelibsiz")

salomlash()
salomlash()
```

|||

#### Ekranda

```text
Assalomu alaykum!
Darsga xush kelibsiz
Assalomu alaykum!
Darsga xush kelibsiz
```

`def` — yaratadi, `nom()` — chaqiradi. Chaqirilmaguncha funksiya ishlamaydi.

---

###### 02 · Parametrlar
## Parametrlar — funksiyaga ma'lumot

```python
def salom(ism):
    print(f"Salom, {ism}!")

salom("Ali")      # Salom, Ali!
salom("Laylo")    # Salom, Laylo!

def yuza(a, b):
    print(a * b)

yuza(5, 3)        # 15
```

|||

### Parametr

Funksiya ichidagi nom: `ism`

### Argument

Chaqirganda beriladigan qiymat: `"Ali"`

### Bir nechta

Vergul bilan: `def yuza(a, b):`

---

###### 03 · return
## return — natijani qaytarish

### print — faqat ko'rsatadi {.qizil}

```python
def kvadrat(x):
    print(x * x)

natija = kvadrat(4)    # 16 chiqadi
print(natija)          # None
```

|||

### return — qiymat beradi {.yashil}

```python
def kvadrat(x):
    return x * x

natija = kvadrat(4)
print(natija + 1)      # 17
```

Qaytgan qiymatni saqlash, qo'shish, boshqa funksiyaga berish mumkin.

---

###### 03 · return
## Bir nechta natija qaytarish

```python
def tortburchak(a, b):
    yuza = a * b
    perimetr = 2 * (a + b)
    return yuza, perimetr

y, p = tortburchak(5, 3)
print(y, p)    # 15 16
```

|||

### return a, b

Bir nechta qiymat kortej bo'lib qaytadi

### y, p = …

Kortejni ochib olamiz (7-dars)

### return dan keyin

Funksiya shu yerda tugaydi

---

###### Amaliyot 1 · 10 daqiqa
## Birinchi funksiyalar

1. `salom(ism)` — «Salom, Ali!» chiqarsin.
2. `kub(x)` — sonning kubini qaytarsin (`return`).
3. `ortacha(a, b, c)` — uch sonning o'rtachasini qaytarsin.
4. `toq_mi(n)` — son toq bo'lsa `True` qaytarsin.

> **Yulduzli topshiriq:** `harf_soni(matn, harf)` — matnda shu harf necha marta borligini qaytarsin.

---

###### 04 · Moslashuvchan funksiyalar
# Funksiyani moslashuvchan qilamiz

Standart qiymatlar, nomli argumentlar va o'zgaruvchilar «hayoti».

`def narx(x, foiz=0):` `f(b=2, a=1)`

---

###### 04 · Moslashuvchan funksiyalar
## Standart qiymat va nomli argument

#### Kod

```python
def salom(ism, til="uz"):
    if til == "uz":
        print(f"Salom, {ism}!")
    else:
        print(f"Hello, {ism}!")

salom("Ali")
salom("Ali", "en")
salom(til="en", ism="Vali")
```

|||

#### Ekranda

```text
Salom, Ali!
Hello, Ali!
Hello, Vali!
```

Standart qiymat berilsa — argumentni yozmasa ham bo'ladi. Nomli argumentda tartib muhim emas.

---

###### 04 · Moslashuvchan funksiyalar
## Mahalliy va global o'zgaruvchi

### Mahalliy {.qizil}

```python
def hisob():
    x = 10       # faqat ichkarida
    print(x)

hisob()          # 10
print(x)         # NameError
```

|||

### Global {.yashil}

```python
kurs = 12750

def dollar(som):
    return round(som / kurs, 2)

print(dollar(100000))   # 7.84
```

Funksiya ichida yaratilgan o'zgaruvchi tashqarida ko'rinmaydi. Tashqaridagini esa o'qish mumkin.

---

###### 04 · Moslashuvchan funksiyalar
## Kichik funksiyalardan katta dastur

```python
def ortacha(baholar):
    return sum(baholar) / len(baholar)

def daraja(ball):
    if ball >= 4.5:
        return "A'lo"
    if ball >= 3.5:
        return "Yaxshi"
    return "Qoniqarli"

o = ortacha([5, 4, 5, 4])
print(o, daraja(o))    # 4.5 A'lo
```

|||

### Bitta ish

Har funksiya bitta vazifani bajaradi

### Birlashtirish

Bir funksiya natijasi — boshqasiga argument

### Nomlash

Fe'l bilan: `hisobla`, `korsat`, `saqla`

---

###### 04 · Moslashuvchan funksiyalar
## Yangi boshlovchilarning 4 xatosi

### 1. Qavsni unutish

```diff
- salom            hech narsa bo'lmaydi
+ salom()
```

### 2. return o'rniga print

```diff
-     print(x * x)    natija → None
+     return x * x
```

### 3. Argumentlar soni

```diff
- yuza(5)          TypeError
+ yuza(5, 3)
```

### 4. def dan oldin chaqirish

```diff
- salom()  # def yuqorida emas   NameError
+ def salom(): ...
+ salom()
```

---

###### Amaliyot 2 · 10 daqiqa
## Funksiyalar kutubxonasi

1. `eng_kichik(royxat)` — `min()` ishlatmasdan eng kichigini qaytarsin.
2. `unli_soni(matn)` — unlilar sonini qaytarsin.
3. `teskari(matn)` — matnni teskari qaytarsin.
4. Har birini ikki xil qiymat bilan chaqirib, natijani chiqaring.

> **Yulduzli topshiriq:** `fakt(n)` — n! ni sikl bilan hisoblasin; `math.factorial` bilan solishtiring.

---

###### Amaliyot 3 · Mini loyiha · 15 daqiqa
## Kalkulyator funksiyalar bilan

#### Kod

```python
def hisobla(a, amal, b):
    if amal == "+":
        return a + b
    if amal == "-":
        return a - b
    if amal == "*":
        return a * b
    if amal == "/" and b != 0:
        return a / b
    return None

print(hisobla(8, "*", 5))   # 40
print(hisobla(8, "/", 0))   # None
```

|||

#### Endi o'zingiz davom ettiring

1. `**` va `%` amallarini qo'shing.
2. `None` o'rniga «Xato» matnini qaytaring.
3. `input()` bilan so'raydigan `menyu()` funksiyasini yozing.
4. Natijani 2 xonagacha yaxlitlang.

---

###### 05 · Viktorina
## Kompyutersiz ayting: ekranda nima chiqadi?

### 1-savol

```python
def f(x):
    return x + 1
print(f(4))
```

### 2-savol

```python
def g():
    print("A", end="")
g()
g()
```

### 3-savol

```python
def f(a, b=10):
    return a * b
print(f(3))
```

### 4-savol

```python
def f():
    x = 5
print(f())
```

### 5-savol

```python
def f(a, b):
    return a - b
print(f(b=2, a=9))
```

### 6-savol

```python
def f(n):
    return n * 2, n * 3
print(f(2))
```

---

###### 05 · Viktorina
## Javoblar: nechta to'g'ri topdingiz?

### 1-savol

`5`

4 + 1.

### 2-savol

`AA`

Ikki marta chaqirildi, `end=""`.

### 3-savol

`30`

b — standart qiymat 10.

### 4-savol

`None`

return yo'q — natija None.

### 5-savol

`7`

Nomli argument: 9 - 2.

### 6-savol

`(4, 6)`

Ikki qiymat — kortej.

---

###### Xulosa va uyga vazifa
## Bugun nimani o'rgandik

### Esda qoladigan 4 narsa {.sariq}

- `def nom(parametr):` — yaratish, `nom(qiymat)` — chaqirish
- `return` natijani qaytaradi, `print` faqat ko'rsatadi
- Standart qiymat: `def f(x, foiz=0)`
- Funksiya ichidagi o'zgaruvchi — faqat ichkarida

|||

### Uyga vazifa {.qizil}

1. `maydon(a, b)`
2. `juftmi(n)`
3. `eng_katta(a, b, c)`
4. `baho(ball)`
5. `chegirma(narx, foiz=10)`

Batafsil — platformadagi «Uy vazifasi» bo'limida.

::: ustozga

Dars rejasi (2 soat):
- 0–15 daq: 9-dars uy vazifasi (while, tub son).
- 15–35 daq: def va parametrlar (3–5-slaydlar). Funksiyani «retsept»ga o'xshating: def — retseptni yozish, chaqirish — ovqat pishirish.
- 35–55 daq: return (6–7-slaydlar) — darsning eng muhim qismi. print va return farqini None misolida jonli ko'rsating.
- 55–65 daq: Amaliyot 1.
- 65–75 daq: tanaffus.
- 75–95 daq: standart qiymat, nomli argument, mahalliy/global (9–12-slaydlar).
- 95–110 daq: Amaliyot 2 va 3.
- 110–120 daq: viktorina, platformadagi test va uy vazifasi.

Ko'p uchraydigan xatolar: chaqirishda qavsni unutish; return o'rniga print ishlatish va natijani None olish; argumentlar sonini adashtirish (TypeError: missing 1 required positional argument); funksiyani def dan oldin chaqirish; funksiya ichidagi o'zgaruvchini tashqarida ishlatishga urinish.

::: test

? Python'da funksiya qaysi kalit so'z bilan yaratiladi?
+ def
- function
- func
- return
> def — «define» (aniqlash) so'zidan.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
def f(x):
    return x * 3
print(f(4))
```
= 12
> f(4) — 4 * 3.

? Quyidagi kod nima chiqaradi?
```python
def salom(ism):
    print("Salom,", ism)
salom("Ali")
```
+ Salom, Ali
- Salom ism
- Xato beradi
- Hech narsa chiqmaydi
> ism parametri "Ali" qiymatini oladi.

? Quyidagi kod nima chiqaradi?
```python
def f():
    return 5
    print("A")
print(f())
```
+ 5
- A
- 5 va A
- None
> return dan keyingi qatorlar bajarilmaydi.

? Quyidagi kod nima chiqaradi?
```python
def f(x):
    x * 2
print(f(3))
```
+ None
- 6
- 3
- Xato beradi
> return yo'q — funksiya None qaytaradi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
def f(a, b=2):
    return a ** b
print(f(3))
```
= 9
> b berilmadi — standart qiymat 2: 3 ** 2.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
def f(a, b=2):
    return a ** b
print(f(2, 3))
```
= 8
> b = 3 berildi: 2 ** 3.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
def f(a, b):
    return a - b
print(f(b=1, a=10))
```
= 9
> Nomli argumentlar: a = 10, b = 1.

? Quyidagi kod nima bo'ladi?
```python
def f():
    y = 7
f()
print(y)
```
+ NameError xatosi
- 7
- None
- 0
> y — funksiya ichidagi (mahalliy) o'zgaruvchi, tashqarida yo'q.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
def f(n):
    return n, n * 2
a, b = f(5)
print(b)
```
= 10
> f(5) — (5, 10) kortej; b = 10.

? Quyidagi kod nima chiqaradi?
```python
def f(x):
    if x > 0:
        return "musbat"
    return "manfiy yoki nol"
print(f(-3))
```
+ manfiy yoki nol
- musbat
- None
- -3
> -3 > 0 yolg'on, ikkinchi return ishlaydi.

? Funksiyani chaqirganda beriladigan qiymat nima deyiladi?
+ Argument
- Parametr
- Kalit so'z
- Modul
> Parametr — def dagi nom, argument — chaqirganda beriladigan qiymat.

? Funksiya yaratish va ishlatish qatorlarini tartibga qo'ying.
1. def yuza(a, b):
2. return a * b
3. natija = yuza(4, 5)
4. print(natija)

? Tushunchani ma'nosi bilan moslang:
def :: funksiya yaratadi
return :: natijani qaytaradi
parametr :: funksiya ichidagi nom
argument :: chaqirganda beriladigan qiymat

::: uy-vazifasi

5 ta topshiriq — hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying (yoki .py fayl biriktiring). Har topshiriq oldidan izoh yozing: # 1-topshiriq, # 2-topshiriq va h.k.
Har topshiriqda funksiya natijani return bilan qaytarsin, chiqarish — print bilan funksiyadan tashqarida.

1-topshiriq. Maydon
maydon(a, b) funksiyasi to'g'ri to'rtburchak yuzasini qaytarsin. maydon(5, 8) natijasini chiqaring.

Kutilgan natija:
40

2-topshiriq. Juftmi
juftmi(n) — son juft bo'lsa True, aks holda False qaytarsin. juftmi(10) va juftmi(7) ni chiqaring.

Kutilgan natija:
True
False

3-topshiriq. Eng kattasi
eng_katta(a, b, c) — max() ishlatmasdan eng kattasini qaytarsin. eng_katta(12, 25, 7) ni chiqaring.

Kutilgan natija:
25

4-topshiriq. Baho
baho(ball) — 90 va yuqori bo'lsa «A», 80–89 «B», 70–79 «C», qolgani «D» qaytarsin. 95, 85, 72 va 50 uchun natijalarni bitta qatorda chiqaring.

Kutilgan natija:
A B C D

5-topshiriq. Chegirma
chegirma(narx, foiz=10) — chegirmadan keyingi narxni butun son qilib qaytarsin. chegirma(200000) va chegirma(200000, 25) ni chiqaring.

Kutilgan natija:
180000
150000
