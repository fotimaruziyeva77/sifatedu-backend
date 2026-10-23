+++
title = "5-mavzu: shartli, mantiqiy va taqqoslash operatorlari"
summary = "Taqqoslash, if / elif / else, and, or, not va rost-yolg'on qiymatlar"
+++

::: slaydlar

###### Python darsi · 5-mavzu
# Shartlar: if, elif, else

Taqqoslash, mantiqiy amallar va o'zi qaror qiladigan dastur

`if yosh >= 18:` `and / or / not` nazariya + 3 ta amaliyot + viktorina

---

###### Bugungi reja
## Darsda nimalarni o'rganamiz?

### 01 Taqqoslash

`== != > < >= <=` — natija True yoki False

### 02 if / else

Agar shart rost bo'lsa — bir ish, aks holda — boshqa

### 03 elif

Bir nechta shartni ketma-ket tekshirish

### 04 Mantiq

`and`, `or`, `not` va rost-yolg'on qiymatlar

---

###### 01 · Muammo
## Dastur o'zi qaror qila oladimi?

### Shartsiz {.qizil}

```python
ball = 45
print("Tabriklaymiz, o'tdingiz!")
# 45 ball bilan ham tabriklayapti...
```

|||

### Shart bilan {.sariq}

```python
ball = 45
if ball >= 60:
    print("Tabriklaymiz, o'tdingiz!")
else:
    print("Qayta topshiring")
```

Dastur vaziyatga qarab har xil ish qiladi.

---

###### 02 · Taqqoslash
## Taqqoslash operatorlari

| Belgi | Ma'nosi | Misol | Natija |
|---|---|---|---|
| `==` | teng | `5 == 5` | `True` |
| `!=` | teng emas | `3 != 3` | `False` |
| `>` | katta | `7 > 2` | `True` |
| `<` | kichik | `7 < 2` | `False` |
| `>=` | katta yoki teng | `5 >= 5` | `True` |
| `<=` | kichik yoki teng | `4 <= 3` | `False` |

`=` — qiymat beradi, `==` — taqqoslaydi. Natija doim `True` yoki `False`.

---

###### 02 · Taqqoslash
## Matn va zanjir taqqoslash

```python
print("a" < "b")          # True
print("olma" == "Olma")   # False
print(2 < 5 < 10)         # True
x = 7
print(5 < x < 10)         # True
```

|||

### Matnlar

Alifbo tartibida taqqoslanadi

### Katta-kichik harf

"olma" va "Olma" — har xil matn

### Zanjir

`2 < 5 < 10` — ikkala shart birga

---

###### 03 · if / else
## if — agar shart rost bo'lsa

#### Kod

```python
yosh = 20
if yosh >= 18:
    print("Kirish mumkin")
print("Tamom")
```

|||

#### Ekranda

```text
Kirish mumkin
Tamom
```

Ikki nuqta `:` va 4 bo'sh joy (indent) majburiy. Indentli qatorlar faqat shart rost bo'lsa bajariladi.

---

###### 03 · if / else
## if / else — ikki yo'l

### Yosh

```python
yosh = 16
if yosh >= 18:
    print("katta")
else:
    print("kichik")
```

```text
kichik
```

|||

### Juft yoki toq

```python
son = 24
if son % 2 == 0:
    print("juft")
else:
    print("toq")
```

```text
juft
```

---

###### 03 · if / else
## elif — bir nechta shart

#### Kod

```python
ball = 85
if ball >= 90:
    print("A")
elif ball >= 80:
    print("B")
elif ball >= 70:
    print("C")
else:
    print("D")
```

|||

#### Ekranda

```text
B
```

Shartlar yuqoridan pastga tekshiriladi: **birinchi** rost bo'lgani bajariladi, qolganlari o'tkazib yuboriladi.

---

###### Amaliyot 1 · 10 daqiqa
## Qaror qabul qilamiz

1. Son so'rang: musbat, manfiy yoki nolmi — chiqaring.
2. Ikki sondan kattasini `if` bilan toping (`max()` siz).
3. Harorat: 30 dan yuqori — «Issiq», 10 dan past — «Sovuq», aks holda — «Iliq».
4. Yosh: 7–17 — «O'quvchi», 18 va katta — «Katta yoshli».

> **Yulduzli topshiriq:** son 3 ga ham, 5 ga ham bo'linsa — «FizzBuzz», faqat 3 ga — «Fizz», faqat 5 ga — «Buzz».

---

###### 04 · Mantiq
# and, or, not — shartlarni birlashtiramiz

Bir nechta shartni bitta if da tekshirish.

`and` `or` `not`

---

###### 04 · Mantiq
## Mantiqiy amallar

| Amal | Qachon True? | Misol | Natija |
|---|---|---|---|
| `and` | ikkalasi ham rost | `5 > 3 and 2 > 1` | `True` |
| `and` | bittasi yolg'on | `10 > 3 and 2 > 5` | `False` |
| `or` | kamida bittasi rost | `10 > 3 or 2 > 5` | `True` |
| `or` | ikkalasi yolg'on | `1 > 3 or 2 > 5` | `False` |
| `not` | teskarisi | `not 5 > 3` | `False` |

---

###### 04 · Mantiq
## Hayotiy misol: kirish tizimi

#### Kod

```python
login = "admin"
parol = "1234"
if login == "admin" and parol == "1234":
    print("Xush kelibsiz!")
else:
    print("Login yoki parol xato")
```

|||

#### Ekranda

```text
Xush kelibsiz!
```

`and` — ikkala shart ham bajarilishi kerak: login ham, parol ham.

---

###### 04 · Mantiq
## Rost va yolg'on qiymatlar

```python
print(bool(0))         # False
print(bool(""))        # False
print(bool([]))        # False
print(bool(5))         # True
print(bool("salom"))   # True
```

|||

### Yolg'on

`0`, bo'sh matn `""`, bo'sh ro'yxat `[]`, `None`

### Rost

Qolgan hamma narsa

### if n:

n nolga teng bo'lmasa bajariladi

---

###### 04 · Mantiq
## Yangi boshlovchilarning 4 xatosi

### 1. = o'rniga ==

```diff
- if x = 5:          SyntaxError
+ if x == 5:
```

### 2. Ikki nuqta yo'q

```diff
- if x > 5           SyntaxError
+ if x > 5:
```

### 3. Indent yo'q

```diff
- print("katta")     IndentationError
+     print("katta")
```

### 4. Matn va son

```diff
- if yosh > "18":    TypeError
+ if yosh > 18:
```

---

###### Amaliyot 2 · 10 daqiqa
## Do'kon chegirmasi

1. Xarid summasini `input()` bilan so'rang.
2. 500 000 dan ko'p bo'lsa — 10% chegirma, 1 000 000 dan ko'p bo'lsa — 20%.
3. Chegirma summasini va to'lovni chiqaring.
4. Summa 0 yoki manfiy bo'lsa — «Noto'g'ri summa».

> **Yulduzli topshiriq:** kunni ham so'rang: shanba yoki yakshanba bo'lsa, yana 5% chegirma (`or`).

---

###### Amaliyot 3 · Mini loyiha · 15 daqiqa
## Kalkulyator

#### Kod

```python
a = float(input("1-son: "))
amal = input("Amal (+ - * /): ")
b = float(input("2-son: "))
if amal == "+":
    print(a + b)
elif amal == "-":
    print(a - b)
elif amal == "*":
    print(a * b)
elif amal == "/":
    print(a / b)
else:
    print("Noma'lum amal")
```

|||

#### Endi o'zingiz davom ettiring

1. 0 ga bo'lishda «Nolga bo'lib bo'lmaydi» deng.
2. `**` va `%` amallarini qo'shing.
3. Natijani 2 xonagacha yaxlitlang.
4. «5.0 + 3.0 = 8.0» ko'rinishida chiqaring.

---

###### 05 · Viktorina
## Kompyutersiz ayting: ekranda nima chiqadi?

### 1-savol

```python
print(5 > 3 and 3 > 4)
```

### 2-savol

```python
print(not False)
```

### 3-savol

```python
x = 10
print(x > 5 or x < 0)
```

### 4-savol

```python
print(7 != 7)
```

### 5-savol

```python
print(bool(0))
```

### 6-savol

```python
print(2 < 5 < 4)
```

---

###### 05 · Viktorina
## Javoblar: nechta to'g'ri topdingiz?

### 1-savol

`False`

3 > 4 yolg'on: `and` uchun bittasi yetarli.

### 2-savol

`True`

`not` teskarisini beradi.

### 3-savol

`True`

`or` uchun bittasi rost bo'lsa yetadi.

### 4-savol

`False`

7 = 7, «teng emas» — yolg'on.

### 5-savol

`False`

0 — yolg'on qiymat.

### 6-savol

`False`

5 < 4 yolg'on — zanjir buziladi.

---

###### Xulosa va uyga vazifa
## Bugun nimani o'rgandik

### Esda qoladigan 4 narsa {.sariq}

- `==` taqqoslaydi, `=` qiymat beradi
- `if` / `elif` / `else`: ikki nuqta va 4 bo'sh joy
- `and` — ikkalasi, `or` — bittasi, `not` — teskari
- `0`, `""`, `[]` — yolg'on qiymatlar

|||

### Uyga vazifa {.qizil}

1. Juft yoki toq
2. Ball bo'yicha baho
3. Kabisa yili
4. Uch sonning eng kattasi (`max` siz)
5. Login va parol

Batafsil — platformadagi «Uy vazifasi» bo'limida.

::: ustozga

Dars rejasi (2 soat):
- 0–15 daq: 4-dars uy vazifasi (math, round).
- 15–35 daq: taqqoslash (3–5-slaydlar). Har operator uchun o'quvchidan misol so'rang; = va == farqini alohida ta'kidlang.
- 35–55 daq: if / else / elif (6–8-slaydlar). Indentni doskada ko'rsating: 4 bo'sh joy yoki Tab — aralashtirmaslik kerak.
- 55–65 daq: Amaliyot 1.
- 65–75 daq: tanaffus.
- 75–95 daq: and / or / not, rost-yolg'on qiymatlar, ko'p uchraydigan xatolar (10–14-slaydlar). Mantiq jadvalini o'quvchilar o'zi to'ldirsin.
- 95–110 daq: Amaliyot 2 va 3 (kalkulyator).
- 110–120 daq: viktorina, platformadagi test va uy vazifasi.

Ko'p uchraydigan xatolar: if x = 5 (bitta =); ikki nuqtani unutish; indentsiz yoki aralash indent; input() natijasini songa o'girmasdan taqqoslash (TypeError: '>' not supported between instances of 'str' and 'int'); elif tartibini noto'g'ri qo'yish (ball >= 70 avval tekshirilsa, 95 ham C bo'lib qoladi).

::: test

? Quyidagi kod nima chiqaradi?
```python
print(10 > 3 and 2 > 5)
```
+ False
- True
- 10
- Xato beradi
> and — ikkala shart ham rost bo'lishi kerak; 2 > 5 yolg'on.

? Quyidagi kod nima chiqaradi?
```python
print(10 > 3 or 2 > 5)
```
+ True
- False
- 2
- Xato beradi
> or — kamida bittasi rost bo'lsa yetarli.

? Quyidagi kod nima chiqaradi?
```python
print(not 5 > 3)
```
+ False
- True
- 5
- Xato beradi
> Avval 5 > 3 = True, keyin not True = False.

? Quyidagi kod nima chiqaradi?
```python
yosh = 16
if yosh >= 18:
    print("katta")
else:
    print("kichik")
```
+ kichik
- katta
- katta kichik
- Hech narsa chiqmaydi

? Quyidagi kod nima chiqaradi?
```python
n = 0
if n:
    print("bor")
else:
    print("yo'q")
```
+ yo'q
- bor
- 0
- Xato beradi
> 0 soni shartda False hisoblanadi.

? Quyidagi kod nima chiqaradi?
```python
print(3 != 3)
```
+ False
- True
- 3
- Xato beradi

? Quyidagi kod nima chiqaradi?
```python
print(5 >= 5)
```
+ True
- False
- 5
- Xato beradi
> >= — katta yoki teng; 5 = 5.

? Quyidagi kod nima chiqaradi?
```python
ball = 85
if ball >= 90:
    print("A")
elif ball >= 80:
    print("B")
elif ball >= 70:
    print("C")
else:
    print("D")
```
+ B
- A
- C
- D
> Shartlar tepadan tekshiriladi; birinchi rost shart — ball >= 80.

? Quyidagi kod nima chiqaradi?
```python
print("a" < "b")
```
+ True
- False
- Xato beradi
- a
> Matnlar alifbo tartibida solishtiriladi.

? Quyidagi kod nima chiqaradi?
```python
print(2 < 5 < 10)
```
+ True
- False
- Xato beradi
- 5
> Python'da taqqoslashni zanjir qilib yozish mumkin: 2 < 5 va 5 < 10.

? x = 7 bo'lsa, qaysi shart rost?
+ x % 2 == 1
- x % 2 == 0
- x > 10
- x == "7"
> 7 toq son: 2 ga bo'linganda qoldiq 1. 7 va "7" — har xil turlar.

? Python'da "teng" taqqoslash operatori qaysi?
+ ==
- =
- ===
- eq
> = — qiymat berish, == — taqqoslash.

? Quyidagi kod nima chiqaradi?
```python
print(True and not False)
```
+ True
- False
- None
- Xato beradi

? Ifodani ma'nosi bilan moslang:
a == b :: a va b teng
a != b :: a va b teng emas
a >= b :: a b dan katta yoki teng
a <= b :: a b dan kichik yoki teng

::: uy-vazifasi

5 ta topshiriq — hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying (yoki .py fayl biriktiring). Har topshiriq oldidan izoh yozing: # 1-topshiriq, # 2-topshiriq va h.k.
input() bilan ishlaydigan topshiriqlarda misoldagi qiymatni kiritib tekshiring.

1-topshiriq. Juft yoki toq
Sonni input() bilan so'rang va juft yoki toqligini chiqaring (% dan foydalaning).

Kutilgan natija (37 kiritilsa):
37 — toq son

2-topshiriq. Baho
Ballni input() bilan so'rang (0–100). 86–100 — 5 (a'lo), 71–85 — 4 (yaxshi), 55–70 — 3 (qoniqarli), 0–54 — 2 (qoniqarsiz). Ball 0 dan kichik yoki 100 dan katta bo'lsa — «Noto'g'ri ball».

Kutilgan natija (76 kiritilsa):
Baho: 4 (yaxshi)

3-topshiriq. Kabisa yili
Yil 4 ga bo'linsa va 100 ga bo'linmasa, yoki 400 ga bo'linsa — kabisa yili. Kodni yil o'zgaruvchisi bilan yozing va yil = 2024, 1900, 2000 qiymatlarida tekshirib ko'ring.

Kutilgan natija (yil = 2024, 1900 va 2000 bo'lganda):
2024 — kabisa yili
1900 — kabisa yili emas
2000 — kabisa yili

4-topshiriq. Uch sonning eng kattasi
a = 12, b = 27, c = 9. max() ishlatmasdan, if / elif / else va and bilan eng kattasini toping.

Kutilgan natija:
Eng katta: 27

5-topshiriq. Login
To'g'ri login — "admin", parol — "sifat2026". Login va parolni input() bilan so'rang. Ikkalasi to'g'ri — «Xush kelibsiz!»; login noto'g'ri — «Bunday foydalanuvchi yo'q»; login to'g'ri, parol noto'g'ri — «Parol noto'g'ri».

Kutilgan natija (admin va 1234 kiritilsa):
Parol noto'g'ri
