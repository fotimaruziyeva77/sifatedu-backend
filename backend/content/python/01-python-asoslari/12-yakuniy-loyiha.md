+++
title = "12-mavzu: yakuniy loyiha — «Do'kon kassasi»"
summary = "Bir oyda o'rganilganlarni bitta dasturga yig'ish: lug'at, funksiyalar, menyu, try / except va fayl"
homework_title = "Yakuniy loyiha: «Do'kon kassasi»"
+++

::: slaydlar

###### Python darsi · 12-mavzu
# Yakuniy loyiha: Do'kon kassasi

Bir oyda o'rganganlarimizni bitta haqiqiy dasturga yig'amiz

`def` `dict` `while True` `with open` loyiha + himoya + viktorina

---

###### Bugungi reja
## Darsda nimalarni qilamiz?

### 01 Reja

Kassa dasturi nima qilishi kerak

### 02 Ma'lumot

Mahsulotlar lug'ati va savat

### 03 Funksiyalar

Har bir amal — alohida funksiya

### 04 Himoya

Loyihani guruhga taqdim etish

---

###### 01 · Reja
## Kassa dasturi nima qiladi?

### 01 Mahsulotlar

Narxlar ro'yxatini ko'rsatadi

### 02 Savat

Mahsulot va sonini qo'shadi

### 03 Chek

Jami, chegirma va to'lov

### 04 Saqlash

Chekni faylga yozadi

---

###### 01 · Reja
## Bir oyda o'rganganimiz — hammasi kerak bo'ladi

| Mavzu | Loyihada qayerda |
|---|---|
| `print`, f-string | chekni chiroyli chiqarish |
| `input`, `int` | mahsulot va sonini so'rash |
| `if` / `elif` | menyudagi tanlov |
| `dict` | narxlar va savat |
| `for` | chekdagi har bir qator |
| `while True` | menyu qayta-qayta chiqadi |
| `def` | har bir amal — funksiya |
| `try` / `except` | noto'g'ri kiritishda yiqilmaslik |
| `with open` | chekni faylga saqlash |

---

###### 02 · Ma'lumot
## Mahsulotlar va savat

```python
mahsulotlar = {
    "non": 4000,
    "sut": 12000,
    "tuxum": 1500,
    "choy": 15000,
}
savat = {}    # nom: soni
```

|||

### Narxlar — dict

Nom bo'yicha narx: `mahsulotlar["non"]`

### Savat — dict

Nom: soni. Bir xil mahsulot yana qo'shilsa — soni oshadi.

---

###### 03 · Funksiyalar
## 1-qadam: mahsulotlarni ko'rsatish

#### Kod

```python
def korsat():
    for nom, narx in mahsulotlar.items():
        print(f"{nom:6} {narx:>6} so'm")

korsat()
```

|||

#### Ekranda

```text
non      4000 so'm
sut     12000 so'm
tuxum    1500 so'm
choy    15000 so'm
```

`{nom:6}` — 6 belgilik joy, `{narx:>6}` — o'ngga tekislash: ustunlar tekis turadi.

---

###### 03 · Funksiyalar
## 2-qadam: savatga qo'shish

```python
def qosh(nom, soni):
    if nom not in mahsulotlar:
        print("Bunday mahsulot yo'q")
        return
    savat[nom] = savat.get(nom, 0) + soni
    print(f"{nom} x {soni} qo'shildi")

qosh("non", 2)     # non x 2 qo'shildi
qosh("non", 1)     # non x 1 qo'shildi
qosh("kola", 1)    # Bunday mahsulot yo'q
print(savat)       # {'non': 3}
```

|||

### not in

Lug'atda yo'qmi — tekshiradi

### savat.get(nom, 0)

Yo'q bo'lsa 0 dan boshlaydi

### return

Xato bo'lsa — funksiyadan chiqamiz

---

###### 03 · Funksiyalar
## 3-qadam: chek va chegirma

#### Kod

```python
def chek():
    jami = 0
    for nom, soni in savat.items():
        summa = mahsulotlar[nom] * soni
        print(f"{nom:6} {soni:>2} ta {summa:>7}")
        jami += summa
    if jami >= 100000:
        jami = jami * 95 // 100
        print("Chegirma: 5%")
    print("Jami:", jami, "so'm")
    return jami

qosh("choy", 7)
chek()
```

|||

#### Ekranda

```text
choy x 7 qo'shildi
non     3 ta   12000
choy    7 ta  105000
Chegirma: 5%
Jami: 111150 so'm
```

---

###### 03 · Funksiyalar
## 4-qadam: xavfsiz kiritish

```python
def so_ra():
    nom = input("Mahsulot: ").strip().lower()
    try:
        soni = int(input("Soni: "))
    except ValueError:
        print("Soni — butun son bo'lsin!")
        return
    qosh(nom, soni)
```

|||

### strip().lower()

« Non » ham «non» bo'ladi

### try / except

«ikki» deb yozsa ham dastur yiqilmaydi

### qosh()

Tayyor funksiyani qayta ishlatamiz

---

###### 03 · Funksiyalar
## 5-qadam: menyu — dasturning yuragi

#### Kod

```python
while True:
    tanlov = input("1-ro'yxat 2-qo'shish 3-chek 0-chiqish: ")
    if tanlov == "1":
        korsat()
    elif tanlov == "2":
        so_ra()
    elif tanlov == "3":
        saqla(chek())
    elif tanlov == "0":
        print("Xayr!")
        break
    else:
        print("Noto'g'ri tanlov")
```

|||

#### Esda tuting

Har bir tanlov — bitta funksiya chaqiruvi. Menyu qisqa va tushunarli bo'lib qoladi.

`saqla(chek())` — chek natijasi darhol faylga yoziladi.

---

###### 03 · Funksiyalar
## 6-qadam: chekni faylga saqlash

```python
from datetime import datetime

def saqla(jami):
    vaqt = datetime.now().strftime("%d.%m.%Y %H:%M")
    with open("cheklar.txt", "a", encoding="utf-8") as f:
        f.write(f"{vaqt} — {jami} so'm\n")
```

### datetime.now()

Hozirgi sana va vaqt

### "a" rejim

Har chek oxiriga qo'shiladi

### Natija

`23.10.2026 15:40 — 111150 so'm`

---

###### Amaliyot · 40 daqiqa
## Kassani yig'amiz

1. Barcha funksiyalarni bitta `kassa.py` fayliga yig'ing va menyuni ishga tushiring.
2. 3 ta mahsulot qo'shib, chek oling.
3. Savatdan o'chirish: `ochir(nom)` funksiyasini qo'shing.
4. `cheklar.txt` ni oching — cheklar saqlanganini tekshiring.

> **Yulduzli topshiriq:** «Kunlik hisobot»: cheklar.txt dagi barcha summalarni yig'ib, kunlik tushumni chiqaring.

---

###### 04 · Himoya
# Loyihani himoya qilamiz

Har bir o'quvchi 3 daqiqada o'z kassasini ko'rsatadi.

`python kassa.py`

---

###### 04 · Himoya
## Himoya rejasi: 3 daqiqa

### 01 Ishga tushirish

Dastur xatosiz ochiladi

### 02 Ko'rsatish

Mahsulot qo'shish va chek olish

### 03 Kod

Eng qiziq funksiyangizni tushuntiring

### 04 Savollar

Guruhdoshlar 1–2 savol beradi

---

###### 04 · Himoya
## Baholash mezonlari

| Mezon | Ball |
|---|---|
| Dastur ishlaydi, xato bermaydi | 30 |
| Kod funksiyalarga ajratilgan | 20 |
| Noto'g'ri kiritishda yiqilmaydi (`try`) | 15 |
| Chek to'g'ri hisoblangan va chiroyli | 15 |
| Cheklar faylga saqlanadi | 10 |
| Qo'shimcha imkoniyat: o'chirish, hisobot | 10 |

Jami — 100 ball. 85 va undan yuqori — a'lo.

---

###### 05 · Viktorina
## Bir oyni takrorlaymiz: ekranda nima chiqadi?

### 1-savol

```python
print(len("Python") * 2)
```

### 2-savol

```python
a = [3, 1, 2]
a.sort()
print(a[-1])
```

### 3-savol

```python
d = {"non": 4000}
print(d.get("sut", 0))
```

### 4-savol

```python
s = 0
for i in range(1, 4):
    s += i
print(s)
```

### 5-savol

```python
def f(x=2):
    return x ** 3
print(f())
```

### 6-savol

```python
try:
    print(int("3.5"))
except ValueError:
    print("xato")
```

---

###### 05 · Viktorina
## Javoblar: nechta to'g'ri topdingiz?

### 1-savol

`12`

6 ta harf × 2.

### 2-savol

`3`

Saralangach oxirgisi — eng kattasi.

### 3-savol

`0`

"sut" yo'q — get() 0 beradi.

### 4-savol

`6`

1 + 2 + 3.

### 5-savol

`8`

Standart qiymat: 2 ** 3.

### 6-savol

`xato`

"3.5" — butun son emas.

---

###### Xulosa va uyga vazifa
## Bir oyda nimani o'rgandik

### Esda qoladigan 4 narsa {.sariq}

- Asoslar: o'zgaruvchi, tur, shart, sikl
- To'plamlar: `list`, `tuple`, `dict`, `set`
- Funksiyalar, modullar, fayllar, `try` / `except`
- Birinchi to'liq dastur — Do'kon kassasi

|||

### Uyga vazifa {.qizil}

1. Savatga qo'shish: `qosh()`
2. Chek: `chek()`
3. Chegirma: `chegirma(jami)`
4. Xavfsiz son: `son_sora()`
5. Menyu va fayl — to'liq kassa

Keyingi oy: Django — saytlar va ma'lumotlar bazasi.

::: ustozga

Dars rejasi (2 soat):
- 0–10 daq: 11-dars uy vazifasi (fayl, try).
- 10–20 daq: loyiha rejasi (2–4-slaydlar). O'quvchilar bilan birga «kassa nima qilishi kerak» ro'yxatini doskada tuzing.
- 20–50 daq: 5–11-slaydlar — har qadamni birga yozing va darhol ishga tushiring. Bitta katta kod emas, bosqichma-bosqich.
- 50–60 daq: tanaffus.
- 60–100 daq: Amaliyot — o'quvchilar kassani o'zi yig'adi; ustoz aylanib yordam beradi. Tez bitirganlarga — o'chirish va kunlik hisobot.
- 100–115 daq: himoya (har o'quvchiga 2–3 daqiqa) — baholash mezonlari slaydi bo'yicha.
- 115–120 daq: viktorina va keyingi oy haqida.

Ko'p uchraydigan xatolar: funksiyani chaqirmasdan e'lon qilib qo'yish; savat lug'atini funksiya ichida yaratib, har safar bo'shatib yuborish; chek() natijasini return qilmaslik (saqla(None)); input() dagi bo'sh joy va katta harf (strip, lower); "w" rejimda cheklar faylini har safar o'chirib yuborish.

::: test

? Quyidagi kod nima chiqaradi?
```python
print(type(3 / 1))
```
+ <class 'float'>
- <class 'int'>
- 3
- 3.0
> / doim float beradi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print("Kassa"[::-1])
```
= assaK
> [::-1] — matnni teskari o'qiydi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(round(7.456, 1))
```
= 7.5
> Verguldan keyin 1 xona: 7.456 → 7.5.

? Quyidagi kod nima chiqaradi?
```python
x = 15
if x % 3 == 0 and x % 5 == 0:
    print("FizzBuzz")
else:
    print(x)
```
+ FizzBuzz
- 15
- Fizz
- Buzz
> 15 ham 3 ga, ham 5 ga bo'linadi.

? Quyidagi kod nima chiqaradi?
```python
a = [5, 2, 8]
a.append(1)
print(sorted(a))
```
+ [1, 2, 5, 8]
- [5, 2, 8, 1]
- [8, 5, 2, 1]
- None
> sorted() yangi saralangan ro'yxat qaytaradi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
d = {"non": 4000, "sut": 12000}
print(sum(d.values()))
```
= 16000
> values() — narxlar: 4000 + 12000.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
s = {1, 2, 2, 3}
print(len(s))
```
= 3
> To'plamda takrorlar bo'lmaydi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
t = (1, 2, 3)
print(t[1] + t[-1])
```
= 5
> t[1] = 2, t[-1] = 3.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
k = 0
for h in "banan":
    if h == "a":
        k += 1
print(k)
```
= 2
> "banan" da 2 ta "a".

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
n = 10
while n > 1:
    n //= 3
print(n)
```
= 1
> 10 → 3 → 1.

? Quyidagi kod nima chiqaradi?
```python
def f(a, b=5):
    return a + b
print(f(1), f(1, 1))
```
+ 6 2
- 6 6
- 2 2
- Xato beradi
> f(1) — b = 5; f(1, 1) — b = 1.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
try:
    x = int("abc")
except ValueError:
    x = 0
print(x + 1)
```
= 1
> int("abc") xato — except da x = 0.

? Kassa dasturi qadamlarini tartibga qo'ying.
1. Mahsulotlar lug'atini yaratish
2. Savatga mahsulot qo'shish
3. Chekni hisoblash
4. Chekni faylga saqlash

? Vazifani kerakli vosita bilan moslang:
Narxlarni nom bo'yicha saqlash :: dict
Menyuni qayta-qayta ko'rsatish :: while True
Noto'g'ri kiritishda yiqilmaslik :: try / except
Chekni saqlash :: with open

::: uy-vazifasi

Yakuniy loyiha: «Do'kon kassasi». 1–4-topshiriqlar — kassaning funksiyalari, 5-topshiriq — hammasini bitta ishlaydigan dasturga yig'ish. Hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying (yoki kassa.py faylini biriktiring). Har topshiriq oldidan izoh yozing: # 1-topshiriq va h.k.

mahsulotlar = {"non": 4000, "sut": 12000, "tuxum": 1500, "choy": 15000}
savat = {}

1-topshiriq. Savatga qo'shish
qosh(nom, soni) funksiyasi mahsulotni savatga qo'shsin va «non x 2 qo'shildi» deb chiqarsin; savatda bor bo'lsa — soni oshsin; mahsulot yo'q bo'lsa — «Bunday mahsulot yo'q». qosh("non", 2), qosh("choy", 1), qosh("non", 1), qosh("kola", 1) dan keyin savatni chiqaring.

Kutilgan natija:
non x 2 qo'shildi
choy x 1 qo'shildi
non x 1 qo'shildi
Bunday mahsulot yo'q
{'non': 3, 'choy': 1}

2-topshiriq. Chek
chek() funksiyasi savatdagi har mahsulot uchun «nom: soni x narx = summa» qatorini va oxirida jami summani chiqarsin (chegirmasiz), jami summani qaytarsin.

Kutilgan natija:
non: 3 x 4000 = 12000
choy: 1 x 15000 = 15000
Jami: 27000 so'm

3-topshiriq. Chegirma
chegirma(jami) — 200 000 va undan ko'p bo'lsa 10%, 100 000 va undan ko'p bo'lsa 5% chegirma bilan to'lov summasini (butun son) qaytarsin. chegirma(27000), chegirma(150000) va chegirma(250000) ni chiqaring.

Kutilgan natija:
27000
142500
225000

4-topshiriq. Xavfsiz son
son_sora(matn) — matnni int ga o'girib qaytarsin; o'girib bo'lmasa yoki son 1 dan kichik bo'lsa — None. son_sora("3"), son_sora("uch") va son_sora("0") ni chiqaring.

Kutilgan natija:
3
None
None

5-topshiriq. To'liq kassa
Hammasini while True menyusiga yig'ing: 1 — mahsulotlar, 2 — qo'shish (input bilan, son_sora orqali), 3 — chek (chegirma bilan), 0 — chiqish. Chek olinganda «sana — summa» qatorini cheklar.txt fayliga qo'shing ("a" rejim). Dastur ishlab turganida 2 ta mahsulot qo'shib, chek oling va ekrandagi natijani ham yuboring.
