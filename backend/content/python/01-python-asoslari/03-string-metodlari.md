+++
title = "3-mavzu: string metodlari"
summary = "Indeks va kesish, matn metodlari, in operatori va f-string"
+++

::: slaydlar

###### Python darsi · 3-mavzu
# Matn bilan ishlash

Indeks, kesish, matn metodlari va f-string

`"Python"[0]` `s.upper()` nazariya + 3 ta amaliyot + viktorina

---

###### Bugungi reja
## Darsda nimalarni o'rganamiz?

### 01 Indeks

Har bir belgining o'rni va `len()`

### 02 Kesish

`[boshi:oxiri:qadam]` — matndan bo'lak olish

### 03 Metodlar

`upper`, `strip`, `replace`, `find`, `split`

### 04 f-string

Matn ichiga qiymat qo'yish

---

###### 01 · Muammo
## Foydalanuvchi har xil yozadi

### Foydalanuvchi yozdi {.qizil}

```text
"   sALOM dUNYO   "
```

Ortiqcha bo'sh joy, harflar aralash. Bazaga shunday saqlasak — tartibsizlik.

|||

### Bizga kerak {.sariq}

```python
matn = "   sALOM dUNYO   "
print(matn.strip().title())    # Salom Dunyo
```

Bitta qator — matn metodlari hammasini to'g'rilaydi.

---

###### 02 · Indeks
## Indeks: sanoq 0 dan boshlanadi

```indeks
s = "Python"
```

```python
s = "Python"
print(s[0])      # P
print(s[-1])     # n
print(len(s))    # 6
print(s[6])      # IndexError: bunday indeks yo'q
```

---

###### 02 · Kesish
## Kesish: matndan bo'lak olish

```python
s = "dasturlash"
s[0:6]      # 'dastur'
s[6:]       # 'lash'
s[:3]       # 'das'
s[::2]      # 'dsuls'
s[::-1]     # 'hsalrutsad'
```

|||

### [boshi : oxiri : qadam]

Boshi kiradi, oxiri kirmaydi.

### Bo'sh qoldirsa bo'ladi

`[:3]` — boshidan, `[6:]` — oxirigacha.

### [::-1] — teskari

Matnni oxiridan boshiga o'qiydi.

---

###### 03 · Metodlar
## Katta va kichik harflar

| Metod | Misol | Natija |
|---|---|---|
| `upper()` | `"Python".upper()` | `'PYTHON'` |
| `lower()` | `"Python".lower()` | `'python'` |
| `title()` | `"salom dunyo".title()` | `'Salom Dunyo'` |
| `capitalize()` | `"dastur".capitalize()` | `'Dastur'` |

**Metod** — matnga nuqta orqali beriladigan buyruq: `matn.metod()`. Qavslar shart!

---

###### 03 · Metodlar
## Tozalash va almashtirish

#### Kod

```python
print("  salom  ".strip())
print("--Ali--".strip("-"))
print("olma".replace("o", "a"))
print("2026-10-23".replace("-", "."))
```

|||

#### Ekranda

```text
salom
Ali
alma
2026.10.23
```

`strip()` chetlardagi bo'sh joyni, `replace(a, b)` hamma `a` larni `b` ga almashtiradi.

---

###### 03 · Metodlar
## Qidirish: find, count, in

`s = "Navoiy viloyati"`

### Qayerda?

```python
s.find("v")     # 2
```

### Topilmasa?

```python
s.find("z")     # -1
```

### Necha marta?

```python
s.count("i")    # 3
```

### Bormi?

```python
"vil" in s      # True
```

### Boshlanishi

```python
s.startswith("Nav")   # True
```

### Tugashi

```python
s.endswith("ti")      # True
```

---

###### 03 · Metodlar
## split() va join(): bo'lish va yopishtirish

#### Kod

```python
gap = "Python o'rganish qiziq"
sozlar = gap.split()
print(sozlar)
print(len(sozlar))
print("-".join(sozlar))
print("a,b,c".split(","))
```

|||

#### Ekranda

```text
['Python', "o'rganish", 'qiziq']
3
Python-o'rganish-qiziq
['a', 'b', 'c']
```

`split()` matnni so'zlarga bo'ladi, `join()` qayta yopishtiradi.

---

###### Amaliyot 1 · 10 daqiqa
## Ism bilan ishlash

1. Ismingizni `input()` bilan so'rang va katta harflarda chiqaring.
2. Ismning birinchi va oxirgi harfini chiqaring (indeks).
3. Ismni teskari chiqaring (`[::-1]`).
4. Ismda nechta "a" borligini toping (`count`).

> **Yulduzli topshiriq:** so'z palindrommi? `soz == soz[::-1]` — «kiyik» va «olma» bilan tekshiring.

---

###### 04 · f-string
# Matn ichiga qiymat qo'yamiz

f harfi va jingalak qavs — eng qulay chiqarish usuli.

`f"Salom, {ism}!"` `f"{ball:.1f}"`

---

###### 04 · f-string
## f-string — qulay chiqarish

#### Kod

```python
ism = "Ali"
ball = 87.456
print(f"{ism}: {ball} ball")
print(f"{ism}: {ball:.1f} ball")
print(f"2 + 3 = {2 + 3}")
print(f"{ism.upper()}: {len(ism)} harf")
```

|||

#### Ekranda

```text
Ali: 87.456 ball
Ali: 87.5 ball
2 + 3 = 5
ALI: 3 harf
```

`{}` ichida o'zgaruvchi ham, ifoda ham bo'ladi. `:.1f` — 1 xona kasr.

---

###### 04 · f-string
## Diqqat: matn o'zgarmaydi

### Kutganimiz bo'lmadi {.qizil}

```python
s = "salom"
s.upper()
print(s)        # salom
s[0] = "S"      # TypeError
```

|||

### To'g'ri {.yashil}

```python
s = "salom"
s = s.upper()
print(s)        # SALOM
```

Metod **yangi** matn qaytaradi — uni o'zgaruvchiga yozing.

---

###### 04 · f-string
## Hayotiy misol: telefon raqami

#### Kod

```python
r = "998901234567"
kod = r[:3]
operator = r[3:5]
qolgani = f"{r[5:8]}-{r[8:10]}-{r[10:]}"
print(f"+{kod} {operator} {qolgani}")
```

|||

#### Ekranda

```text
+998 90 123-45-67
```

Kesish va f-string birga: bazadagi raqam chiroyli ko'rinishga keldi.

---

###### Amaliyot 2 · 10 daqiqa
## Email va gap

1. `email = "ali.valiyev@mail.ru"`: `find("@")` va kesish bilan login va domenni ajrating.
2. Istalgan gapdagi so'zlar sonini toping (`split` va `len`).
3. Gapdagi bo'sh joylarni `_` ga almashtiring (`replace`).
4. f-string bilan «Gapda 5 ta so'z bor» deb chiqaring.

> **Yulduzli topshiriq:** «Ali Valiyev» dan bosh harflarni ajrating va «A.V.» ko'rinishida chiqaring.

---

###### Amaliyot 3 · Mini loyiha · 15 daqiqa
## Login yaratuvchi

#### Kod

```python
ism = input("Ism: ").strip().lower()
fam = input("Familiya: ").strip().lower()
yil = input("Tug'ilgan yil: ")
login = ism + "." + fam + yil[-2:]
print(f"Login: {login}")
```

```text
Ism: Ali
Familiya: Valiyev
Tug'ilgan yil: 2008
Login: ali.valiyev08
```

|||

#### Endi o'zingiz davom ettiring

1. Email yasang: login + "@sifat.uz".
2. Parol: ismning teskarisi + yil.
3. Login 12 belgidan uzun bo'lsa, birinchi 12 tasini oling.
4. Hammasini f-string bilan chiroyli chiqaring.

---

###### 05 · Viktorina
## Kompyutersiz ayting: ekranda nima chiqadi?

### 1-savol

```python
print("Salom"[1])
```

### 2-savol

```python
print(len("Navoiy"))
```

### 3-savol

```python
print("python".upper()[0])
```

### 4-savol

```python
print("olma"[1:3])
```

### 5-savol

```python
print("a-b-c".split("-"))
```

### 6-savol

```python
x = "abc"
x.upper()
print(x)
```

---

###### 05 · Viktorina
## Javoblar: nechta to'g'ri topdingiz?

### 1-savol

`a`

Indeks 0 dan: S — 0, a — 1.

### 2-savol

`6`

N-a-v-o-i-y — 6 ta belgi.

### 3-savol

`P`

Avval PYTHON, keyin 0-belgi.

### 4-savol

`lm`

1 kiradi, 3 kirmaydi.

### 5-savol

`['a', 'b', 'c']`

`split("-")` ro'yxat qaytaradi.

### 6-savol

`abc`

Natija saqlanmadi: x o'zgarmadi.

---

###### Xulosa va uyga vazifa
## Bugun nimani o'rgandik

### Esda qoladigan 4 narsa {.sariq}

- Indeks 0 dan, `-1` — oxirgi belgi
- Kesish: boshi kiradi, oxiri kirmaydi
- Metod yangi matn qaytaradi: `s = s.upper()`
- `f"{qiymat}"` — eng qulay chiqarish

|||

### Uyga vazifa {.qizil}

1. Ismni tartiblash: `strip`, `title`, `len`
2. So'z bilan ishlash: katta harf, teskari, `count`
3. Gap tahlili: `split` va `in`
4. Email: login va domen
5. Chek qatori: f-string

Batafsil — platformadagi «Uy vazifasi» bo'limida.

::: ustozga

Dars rejasi (2 soat):
- 0–15 daq: 2-dars uy vazifasi (input + int).
- 15–35 daq: indeks va kesish (3–5-slaydlar). Doskada «Python» so'zini katakchalarga yozib, ostiga 0..5 va -6..-1 ni qo'ying. [::-1] ni o'quvchilar o'zi topishga harakat qilsin.
- 35–55 daq: metodlar (6–9-slaydlar). Har metodga o'quvchidan bitta o'z misolini so'rang.
- 55–65 daq: Amaliyot 1.
- 65–75 daq: tanaffus.
- 75–95 daq: f-string va «matn o'zgarmaydi» (11–14-slaydlar). s.upper() natijasi yo'qolib qolishini jonli ko'rsating.
- 95–110 daq: Amaliyot 2 va 3.
- 110–120 daq: viktorina, platformadagi test va uy vazifasi.

Ko'p uchraydigan xatolar: kesishda oxirgi indeks kirmasligi; metod natijasini saqlamaslik; find() topilmasa -1 qaytarishini xato deb o'ylash; f harfini unutish (natijada {ism} so'zi o'zi chiqadi); metoddan keyin qavsni unutish (s.upper — natija emas, metodning o'zi).

::: test

? Quyidagi kod nima chiqaradi?
```python
print("Python".lower())
```
+ python
- PYTHON
- Python
- pYTHON
> lower() barcha harflarni kichik qiladi.

? Quyidagi kod nima chiqaradi?
```python
print("salom dunyo".title())
```
+ Salom Dunyo
- Salom dunyo
- SALOM DUNYO
- salom Dunyo
> title() har bir so'zning birinchi harfini katta qiladi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(len("Salom!"))
```
= 6
> len() barcha belgilarni sanaydi, "!" ham belgi.

? Quyidagi kod nima chiqaradi?
```python
print("dastur".capitalize())
```
+ Dastur
- DASTUR
- dastuR
- dastur
> capitalize() faqat birinchi harfni katta qiladi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print("olma".find("m"))
```
= 2
> find() birinchi uchragan o'rinni qaytaradi: o — 0, l — 1, m — 2.

? Quyidagi kod nima chiqaradi?
```python
print("abc".find("z"))
```
+ -1
- 0
- None
- Xato beradi
> Topilmasa, find() -1 qaytaradi.

? Quyidagi kod nima chiqaradi?
```python
print("dasturlash"[0:6])
```
+ dastur
- dastu
- asturl
- dasturl
> Kesim [0:6] — 0 dan 5 gacha (6 kirmaydi).

? Quyidagi kod nima chiqaradi?
```python
print("ab" + "cd".upper())
```
+ abCD
- ABCD
- abcd
- ABcd
> upper() faqat "cd" ga qo'llanadi, keyin matnlar qo'shiladi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(len("  salom  ".strip()))
```
= 5
> strip() chetidagi bo'sh joylarni olib tashlaydi: "salom" — 5 ta harf.

? Quyidagi kod nima chiqaradi?
```python
print("-".join(["a", "b", "c"]))
```
+ a-b-c
- abc
- a b c
- ['a', 'b', 'c']
> join() ro'yxat elementlarini berilgan belgi bilan birlashtiradi.

? Quyidagi kod nima chiqaradi?
```python
print("salom".startswith("sa"))
```
+ True
- False
- sa
- Xato beradi

? Quyidagi kod nima chiqaradi?
```python
print("Ali" in "Alisher")
```
+ True
- False
- Ali
- Xato beradi
> in — matn ichida bormi yoki yo'qligini tekshiradi.

? Quyidagi kod nima chiqaradi?
```python
print("python"[::-1])
```
+ nohtyp
- python
- p
- Xato beradi
> [::-1] — matnni teskari tartibda qaytaradi.

? Metodni vazifasi bilan moslang:
upper() :: katta harfga o'giradi
lower() :: kichik harfga o'giradi
replace() :: matn qismini almashtiradi
split() :: matnni bo'lib, ro'yxat qaytaradi

::: uy-vazifasi

5 ta topshiriq — hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying. Har topshiriq oldidan izoh yozing: # 1-topshiriq, # 2-topshiriq va h.k.

1-topshiriq. Ismni tartiblash
ism = "  aLi vALIyev  ". Bo'sh joylarni olib tashlang va har so'zni bosh harf bilan chiqaring. So'ng tozalangan matn uzunligini chiqaring.

Kutilgan natija:
Ali Valiyev
11

2-topshiriq. So'z bilan ishlash
soz = "Navoiy". Quyidagilarni alohida qatorlarda chiqaring: katta harflarda, teskari, birinchi va oxirgi harf (bitta print bilan), "o" harfi soni.

Kutilgan natija:
NAVOIY
yiovaN
N y
1

3-topshiriq. Gap tahlili
gap = "Python o'rganish qiziqarli va foydali". So'zlar sonini, birinchi so'zni va gapda "va" so'zi borligini (in) chiqaring.

Kutilgan natija:
5
Python
True

4-topshiriq. Email
email = "student2026@gmail.com". find("@") va kesish bilan login va domenni ajrating.

Kutilgan natija:
student2026
gmail.com

5-topshiriq. Chek qatori
mahsulot = "Daftar", narx = 7500, soni = 3. f-string bilan chiqaring.

Kutilgan natija:
Daftar: 3 x 7500 = 22500 so'm
