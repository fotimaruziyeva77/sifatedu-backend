+++
title = "7-mavzu: list, tuple, dict va set"
summary = "Kortej (tuple), lug'at (dict), to'plam (set) va qaysi birini qachon tanlash"
homework_title = "Amaliyot: list, tuple, dict va set (5 ta topshiriq)"
+++

::: slaydlar

###### Python darsi · 7-mavzu
# list, tuple, dict va set

To'rt xil to'plam: qaysi biri qachon kerak

`( "tuple", )` `{"ism": "Ali"}` `{"qizil", "oq"}` nazariya + 3 ta amaliyot + viktorina

---

###### Bugungi reja
## Darsda nimalarni o'rganamiz?

### 01 Tuple

Qulflangan ro'yxat va ochib olish

### 02 Dictionary

Kalit va qiymat juftligi, metodlar

### 03 Set

Takrorlanmas to'plam, birlashma, kesishma

### 04 Taqqoslash

Qaysi birini qachon tanlaymiz

---

###### 01 · Muammo
## Ali necha ball oldi?

### List bilan {.qizil}

```python
ismlar = ["Ali", "Vali", "Sardor"]
ballar = [95, 78, 88]

i = ismlar.index("Ali")
print(ballar[i])    # 95
```

Ikki ro'yxat, avval indeksni topish kerak. Chalkash va sekin.

|||

### Dictionary bilan {.yashil}

```python
ballar = {
    "Ali": 95,
    "Vali": 78,
    "Sardor": 88}
print(ballar["Ali"])    # 95
```

Ism bo'yicha bir qadamda topamiz. Oson va tez.

---

###### 02 · Tuple
# Tuple — qulflangan ro'yxat

Yaratilgandan keyin ichini o'zgartirib bo'lmaydi.

`hafta = ("Du", "Se", "Chor", "Pay", "Ju", "Sha", "Yak")`

---

###### 02 · Tuple
## Tuple yaratish va o'qish

### Oddiy qavs ( )

```python
nuqta = (3, 7)
ranglar = ("qizil", "oq")
bitta = (5,)     # vergul shart!

nuqta[0]         # 3
ranglar[-1]      # 'oq'
len(nuqta)       # 2
```

|||

### Ochib olish (unpacking)

```python
oquvchi = ("Laylo", 14, "7-B")
ism, yosh, sinf = oquvchi
print(ism)     # Laylo
print(yosh)    # 14

a, b = 1, 2
a, b = b, a    # o'rin almashdi
```

---

###### 02 · Tuple
## O'zgartirmoqchi bo'lsak, Python ruxsat bermaydi

```python
hafta = ("Du", "Se", "Chor")
hafta[0] = "Yak"
```

```text
TypeError: 'tuple' object does not support item assignment
```

### Yo'q metodlar

`append`, `insert`, `remove`, `pop`, `sort`

### Bor metodlar

`count`, `index`, `len()`, `in`

### Juda kerak bo'lsa

`list(hafta)` → o'zgartir → `tuple(...)`

---

###### 02 · Tuple
## List yoki Tuple: qaysi birini tanlaymiz?

| | List [ ] | Tuple ( ) |
|---|---|---|
| O'zgartirish | Mumkin | Mumkin emas |
| Tartib va indeks | Bor | Bor |
| Metodlar | Ko'p: append, sort, pop… | Ikkita: count, index |
| Tezlik va xotira | Biroz sekinroq, kattaroq | Tezroq, ixchamroq |
| Qachon kerak | Ma'lumot o'zgarib tursa | Ma'lumot doimiy bo'lsa |

### List

xaridlar ro'yxati, baholar jurnali, o'yindagi ochkolar

### Tuple

hafta kunlari, koordinata (x, y), tug'ilgan sana

---

###### 03 · Dictionary
## Dictionary — lug'at kitobi kabi

Lug'atda **so'z** orqali uning **ma'nosini** topamiz. Python dictionary ham shunday: **kalit** orqali **qiymatni** topadi.

- Kalitlar takrorlanmaydi
- Kalit o'zgarmas tur: `str`, `int`, `tuple`
- Qiymat istalgan tur bo'lishi mumkin
- Qo'shilish tartibi saqlanadi

|||

| Kalit (key) | Qiymat (value) |
|---|---|
| `"olma"` | `"apple"` |
| `"kitob"` | `"book"` |
| `"suv"` | `"water"` |

```python
lugat = {"olma": "apple", "suv": "water"}
print(lugat["suv"])    # water
```

---

###### 03 · Dictionary
## Qiymatni kalit orqali olamiz

```python
talaba = {"ism": "Aziza", "yosh": 17}
print(talaba["ism"])              # Aziza
print(talaba.get("manzil"))       # None
print(talaba.get("manzil", "-"))  # -
print("yosh" in talaba)           # True
print(talaba["manzil"])           # KeyError
```

|||

### d[kalit]

Tez, lekin kalit yo'q bo'lsa — KeyError

### d.get(kalit, x)

Xavfsiz: yo'q bo'lsa None yoki x

### kalit in d

Kalit bormi: True yoki False

---

###### 03 · Dictionary
## Qo'shish, o'zgartirish, o'chirish

```python
talaba = {"ism": "Aziza", "yosh": 17}
talaba["sinf"] = "11-A"     # qo'shish
talaba["yosh"] = 18         # o'zgartirish
del talaba["sinf"]          # o'chirish
print(talaba)
print(talaba.pop("yosh"))   # 18
print(talaba)               # {'ism': 'Aziza'}
```

|||

### Oltin qoida

`d[kalit] = qiymat`: kalit bor bo'lsa — o'zgartiradi, yo'q bo'lsa — qo'shadi.

### O'chirishning 2 yo'li

`del d[kalit]` — shunchaki o'chiradi. `d.pop(kalit)` — o'chirib, qiymatni qaytaradi.

---

###### 03 · Dictionary
## Eng kerakli metodlar

`d = {"a": 1, "b": 2}`

| Metod | Nima qiladi | Natija |
|---|---|---|
| `d.keys()` | Barcha kalitlar | `dict_keys(['a', 'b'])` |
| `d.values()` | Barcha qiymatlar | `dict_values([1, 2])` |
| `d.items()` | Juftliklar (kalit, qiymat) | `dict_items([('a', 1), ('b', 2)])` |
| `len(d)` | Juftliklar soni | `2` |
| `sum(d.values())` | Qiymatlar yig'indisi | `3` |
| `d.pop("a")` | O'chiradi, qiymatni beradi | `1` |

---

###### Amaliyot 1 · 10 daqiqa
## Telefon kitobi

1. 3 ta do'stingiz ismi va telefon raqamidan **kitob** lug'atini tuzing.
2. Bitta do'stning raqamini kalit orqali chiqaring.
3. Yangi do'st qo'shing, bittasining raqamini o'zgartiring.
4. **get()** bilan yo'q ismni so'rang: «Topilmadi» chiqsin.

> **Yulduzli topshiriq:** barcha ismlarni alifbo tartibida chiqaring: `sorted(kitob.keys())`.

---

###### 04 · Set
# Set: har bir element faqat bir marta

Takrorlar o'zi olib tashlanadi, indeks yo'q.

`set([3, 1, 3, 2, 1])` `{1, 2, 3}`

---

###### 04 · Set
## To'plam yaratamiz va boshqaramiz

```python
mevalar = {"olma", "nok", "olma"}
print(len(mevalar))       # 2
s = set([1, 2, 2, 3, 3])
print(s)                  # {1, 2, 3}
s.add(4)
s.discard(10)             # xato bermaydi
print(s)                  # {1, 2, 3, 4}
bosh = set()              # {} — bu dict!
```

|||

### add(x)

Bitta element qo'shadi

### remove(x)

O'chiradi; x yo'q bo'lsa — KeyError

### discard(x)

O'chiradi; yo'q bo'lsa jim turadi

### Tartibsiz

Indeks yo'q: `s[0]` ishlamaydi

---

###### 04 · Set
## Futbol va shaxmat to'garaklari

```python
f = {"Ali", "Vali", "Sardor"}
s = {"Sardor", "Malika", "Jasur"}
print(sorted(f & s))   # ['Sardor']
print(sorted(f - s))   # ['Ali', 'Vali']
print(len(f | s))      # 5
```

|||

### f | s — birlashma {.kok}

Hammasi: Ali, Vali, Sardor, Malika, Jasur

### f & s — kesishma {.yashil}

Ikkalasida ham: Sardor

### f - s — ayirma {.qizil}

Faqat futbolda: Ali, Vali

### f ^ s — simmetrik ayirma {.sariq}

Faqat bittasida: Ali, Vali, Malika, Jasur

---

###### 05 · Taqqoslash
## List, Tuple, Dict yoki Set: qaysi biri qachon?

| | List | Tuple | Dict | Set |
|---|---|---|---|---|
| Yozilishi | `[1, 2, 3]` | `(1, 2, 3)` | `{"a": 1}` | `{1, 2, 3}` |
| Takrorlanish | Mumkin | Mumkin | Kalit — yo'q | Mumkin emas |
| Tartib | Indeks bilan | Indeks bilan | Kalit bilan | Yo'q |
| O'zgaradimi | Ha | Yo'q | Ha | Ha |
| Qachon? | Ketma-ketlik | Doimiy ma'lumot | Nom bo'yicha | Noyob qiymatlar |

---

###### 05 · Taqqoslash
## Yangi boshlovchilarning 4 xatosi

### 1. Bo'sh set yaratish

```diff
- s = {}             bu dict!
+ s = set()
```

### 2. Yo'q kalitga murojaat

```diff
- d["yoq"]           KeyError
+ d.get("yoq", 0)
```

### 3. Setdan indeks bilan olish

```diff
- s[0]               TypeError
+ 1 in s
```

### 4. Bitta elementli tuple

```diff
- t = (5)            bu int!
+ t = (5,)
```

---

###### Amaliyot 2 · 10 daqiqa
## Ikki do'stning qiziqishlari

1. `ali = {"futbol", "shaxmat", "kitob"}`, `vali = {"kitob", "futbol", "suzish"}`.
2. Ikkalasiga ham yoqadiganlarni chiqaring (`&`).
3. Faqat Aliga yoqadiganlarni chiqaring (`-`).
4. Hammasini takrorlanmasdan, alifbo tartibida chiqaring (`|` va `sorted`).

> **Yulduzli topshiriq:** `[3, 1, 3, 2, 1, 2]` dan takrorlarni olib tashlang va saralangan ro'yxat qiling.

---

###### Amaliyot 3 · Mini loyiha · 15 daqiqa
## Do'kon ombori

#### Kod

```python
ombor = {"daftar": 40, "ruchka": 120, "qalam": 0}
tovar = input("Tovar: ")
if ombor.get(tovar, 0) > 0:
    print(tovar, "bor:", ombor[tovar], "ta")
else:
    print(tovar, "tugagan yoki yo'q")
```

```text
Tovar: qalam
qalam tugagan yoki yo'q
```

|||

#### Endi o'zingiz davom ettiring

1. Yangi tovar qo'shing: "o'chirg'ich" — 25 ta.
2. Sotuv: tovar va sonini so'rab, ombordan ayiring.
3. Jami tovarlar sonini chiqaring: `sum(ombor.values())`.
4. Eng ko'p qolgan tovar sonini toping: `max`.

---

###### 06 · Viktorina
## Natija nima chiqadi?

### 1-savol

```python
d = {"a": 1, "a": 2}
print(d)
```

### 2-savol

```python
s = {1, 2, 2, 3, 3}
print(len(s))
```

### 3-savol

```python
d = {"x": 5}
print(d.get("y", 10) + d["x"])
```

### 4-savol

```python
a = {1, 2, 3}
b = {2, 3, 4}
print(a - b, a & b)
```

### 5-savol

```python
t = (10, 20, 30)
print(t[-1])
```

### 6-savol

```python
k = (5)
print(type(k))
```

---

###### 06 · Viktorina
## Javoblar: nechta to'g'ri topdingiz?

### 1-savol

`{'a': 2}`

Kalit takrorlansa, oxirgi qiymat qoladi.

### 2-savol

`3`

Set takrorlarni olib tashlaydi: {1, 2, 3}.

### 3-savol

`15`

"y" yo'q, get() 10 beradi; 10 + 5 = 15.

### 4-savol

`{1} {2, 3}`

Ayirma: faqat a da. Kesishma: ikkalasida.

### 5-savol

`30`

-1 — oxirgi element.

### 6-savol

`<class 'int'>`

Vergul yo'q — demak oddiy son.

---

###### Xulosa va uyga vazifa
## Bugun nimani o'rgandik

### Esda qoladigan 4 narsa {.sariq}

- Tuple `( )` o'zgarmaydi; bitta elementli: `(5,)`
- Dict `{kalit: qiymat}`; xavfsiz o'qish — `get()`
- Set — faqat noyob elementlar; bo'shi — `set()`
- `&` kesishma, `|` birlashma, `-` ayirma

|||

### Uyga vazifa {.qizil}

1. List: baholar jurnali
2. Tuple: hafta kunlari
3. Dict: do'kon narxlari
4. Set: ikki to'garak
5. Hammasi birga: sinf sardori saylovi

Batafsil — platformadagi «Uy vazifasi» bo'limida.

::: ustozga

Dars rejasi (2 soat):
- 0–15 daq: 6-dars uy vazifasi (ro'yxat metodlari).
- 15–35 daq: muammo va tuple (3–7-slaydlar). (5) va (5,) farqini type() bilan jonli ko'rsating.
- 35–55 daq: dictionary (8–11-slaydlar). Lug'at kitobi o'xshatishi: kalit — so'z, qiymat — tarjima. KeyError va get() farqini o'quvchilar o'zi sinab ko'rsin.
- 55–65 daq: Amaliyot 1 (telefon kitobi).
- 65–75 daq: tanaffus.
- 75–95 daq: set va to'plam amallari (13–15-slaydlar). Futbol/shaxmat misolini doskada Venn diagrammasi bilan chizing. To'plam har safar boshqa tartibda chiqishi mumkin — shuning uchun sorted().
- 95–110 daq: taqqoslash jadvali, xatolar, Amaliyot 2 va 3.
- 110–120 daq: viktorina, platformadagi test va uy vazifasi.

Ko'p uchraydigan xatolar: {} ni bo'sh set deb o'ylash; lug'atda yo'q kalitni [] bilan so'rash (KeyError); in lug'atda qiymatni emas, kalitni tekshirishini bilmaslik; to'plamdan indeks bilan element olishga urinish; (5) ni kortej deb o'ylash.

::: test

? Qaysi biri kortej (tuple)?
+ (1, 2, 3)
- [1, 2, 3]
- {1, 2, 3}
- {"a": 1}
> Kortej oddiy qavs bilan yoziladi; [] — ro'yxat, {1, 2} — to'plam, {"a": 1} — lug'at.

? Quyidagi kod nima bo'ladi?
```python
t = (10, 20, 30)
t[0] = 5
print(t)
```
+ Xato beradi (TypeError)
- (5, 20, 30)
- (10, 20, 30)
- (5, 10, 20, 30)
> Kortej o'zgarmas: elementini almashtirib bo'lmaydi.

? Bitta elementli kortej qanday yoziladi?
+ (5,)
- (5)
- [5]
- {5}
> (5) — oddiy son; vergul qo'yilsa, kortej bo'ladi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
x, y = (4, 9)
print(y - x)
```
= 5
> Kortej ochiladi: x = 4, y = 9.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
a = [1, 2]
a.append([3, 4])
print(len(a))
```
= 3
> append() ro'yxatni bitta element qilib qo'shadi: [1, 2, [3, 4]].

? Quyidagi kod nima chiqaradi?
```python
narx = {"olma": 12000, "non": 4000}
print(narx["non"])
```
+ 4000
- non
- 12000
- Xato beradi
> Lug'atdan qiymat kalit orqali olinadi.

? Quyidagi kod nima chiqaradi?
```python
d = {"a": 1}
d["b"] = 2
print(d)
```
+ {'a': 1, 'b': 2}
- {'a': 1}
- {'b': 2}
- Xato beradi
> Yangi kalitga qiymat berilsa, u lug'atga qo'shiladi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
d = {"ali": 5, "vali": 4}
print(d.get("hasan", 0))
```
= 0
> get() kalit topilmasa, ikkinchi qiymatni qaytaradi.

? Quyidagi kod nima bo'ladi?
```python
d = {"ali": 5}
print(d["vali"])
```
+ KeyError xatosi
- None
- 0
- vali
> Lug'atda yo'q kalit [] bilan so'ralsa — KeyError. Xatosiz olish uchun get() bor.

? Quyidagi kod nima chiqaradi?
```python
d = {"olma": 3, "anor": 5}
print(5 in d)
```
+ False
- True
- 5
- Xato beradi
> in lug'atda kalitlarni tekshiradi, qiymatlarni emas.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
d = {"x": 1, "y": 2, "z": 3}
print(sum(d.values()))
```
= 6
> values() — qiymatlar: 1 + 2 + 3 = 6.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
s = set([1, 2, 2, 3, 3, 3])
print(len(s))
```
= 3
> To'plamda takrorlanuvchi element bo'lmaydi: {1, 2, 3}.

? Bo'sh to'plam (set) qanday yaratiladi?
+ set()
- {}
- []
- ()
> {} — bo'sh lug'at (dict); bo'sh to'plam faqat set() bilan yaratiladi.

? Quyidagi kod nima chiqaradi?
```python
a = {1, 2, 3}
b = {2, 3, 4}
print(a & b)
```
+ {2, 3}
- {1, 2, 3, 4}
- {1, 4}
- {1}
> & — ikkala to'plamda ham bor elementlar (kesishma).

? Qaysi turlarga element qo'shish yoki o'chirish mumkin? Bir nechta javob.
+ list
+ dict
+ set
- tuple
> Faqat kortej (tuple) o'zgarmas.

::: uy-vazifasi

5 ta topshiriq — hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying (yoki .py fayl biriktiring). Har topshiriq oldidan izoh yozing: # 1-topshiriq, # 2-topshiriq va h.k.
Yuborishdan oldin kodni ishga tushirib, natijani «Kutilgan natija» bilan solishtiring: yozuvlar biroz farq qilsa bo'ladi, qiymatlar aynan shunday bo'lsin. Javobni qo'lda yozmang (print(31500) emas) — hisoblashni kod qilsin. Sikl (for, while) shart emas.

1-topshiriq. Ro'yxat (list): baholar jurnali
baholar = [5, 3, 4, 5, 2, 4]
1) baholar sonini chiqaring (len);
2) eng yuqori va eng past bahoni chiqaring (max, min);
3) o'rtacha bahoni 2 xonagacha yaxlitlab chiqaring (sum, len, round);
4) 5 baho necha marta borligini chiqaring (count);
5) ro'yxatga yangi 4 bahoni qo'shing (append), kamayish tartibida saralang
   (sort(reverse=True)) va ro'yxatni chiqaring;
6) eng yaxshi 3 ta bahoni kesim bilan chiqaring ([:3]).

Kutilgan natija:
Baholar soni: 6
Eng yuqori: 5
Eng past: 2
O'rtacha: 3.83
5 lar soni: 2
Saralangan: [5, 5, 4, 4, 4, 3, 2]
Eng yaxshi 3 tasi: [5, 5, 4]

2-topshiriq. Kortej (tuple): hafta kunlari
hafta = ("Dushanba", "Seshanba", "Chorshanba", "Payshanba", "Juma", "Shanba", "Yakshanba")
1) birinchi va oxirgi kunni chiqaring (indeks 0 va -1);
2) kunlar sonini chiqaring (len);
3) "Juma" nechanchi indeksda ekanini chiqaring (index);
4) ish kunlarini — birinchi 5 tasini kesim bilan chiqaring ([:5]);
5) "Shanba" kortejda bormi — tekshirib chiqaring (in);
6) nuqta = (3, 7) kortejini ikki o'zgaruvchiga oching (x, y = nuqta) va x + y, x * y ni
   chiqaring;
7) kortejni nega o'zgartirib bo'lmasligini bitta izoh (#) bilan yozing.

Kutilgan natija:
Birinchi: Dushanba
Oxirgi: Yakshanba
Kunlar soni: 7
Juma indeksi: 4
Ish kunlari: ('Dushanba', 'Seshanba', 'Chorshanba', 'Payshanba', 'Juma')
Shanba bormi: True
x + y = 10
x * y = 21

3-topshiriq. Lug'at (dict): do'kon narxlari
narxlar = {"olma": 12000, "non": 4000, "sut": 9000}
1) nonning narxini chiqaring;
2) "choy" ni 15000 narx bilan qo'shing;
3) non narxini 4500 ga o'zgartiring;
4) "sut" ni o'chiring (pop yoki del) va lug'atni chiqaring;
5) mahsulotlar sonini chiqaring (len);
6) barcha narxlar yig'indisini chiqaring (sum va values());
7) "shakar" narxini get() bilan oling: bo'lmasa 0 chiqsin;
8) eng qimmat narxni chiqaring (max va values()).

Kutilgan natija:
Non: 4000
{'olma': 12000, 'non': 4500, 'choy': 15000}
Mahsulotlar soni: 3
Jami: 31500
Shakar: 0
Eng qimmat narx: 15000

4-topshiriq. To'plam (set): ikki to'garak
python = {"Ali", "Vali", "Hasan", "Olim", "Zarina"}
dizayn = {"Vali", "Zarina", "Sardor", "Madina"}
To'plam har safar boshqa tartibda chiqishi mumkin, shuning uchun ro'yxatlarni sorted() bilan
tartiblab chiqaring.
1) ikkala to'garakka ham qatnashadiganlar (&);
2) hamma o'quvchilar, takrorlanmasdan (|);
3) faqat Python'ga qatnashadiganlar (-);
4) jami nechta turli o'quvchi borligi (len);
5) dizayn to'plamiga "Ali" ni qo'shing (add) va Ali endi ikkala to'garakda ham bormi —
   tekshirib chiqaring (in va and).

Kutilgan natija:
Ikkalasida: ['Vali', 'Zarina']
Hammasi: ['Ali', 'Hasan', 'Madina', 'Olim', 'Sardor', 'Vali', 'Zarina']
Faqat Python: ['Ali', 'Hasan', 'Olim']
Jami o'quvchilar: 7
Ali ikkalasida: True

5-topshiriq. Hammasi birga: sinf sardori saylovi
ovozlar = ["Ali", "Vali", "Ali", "Hasan", "Vali", "Ali"]
1) nomzodlarni takrorlanmasdan, alifbo tartibida chiqaring (set va sorted);
2) natija lug'atini tuzing: har nomzodning ovozlari soni count() bilan, kalitlar tartibi —
   Ali, Vali, Hasan; lug'atni chiqaring;
3) eng ko'p ovoz sonini chiqaring (max va values());
4) jami ovozlar sonini chiqaring (len) va lug'atdagi ovozlar yig'indisi unga tengligini
   tekshiring (sum(...) == len(...));
5) g'olibni if / elif / else bilan toping: kimning ovozi eng ko'p ovozga teng;
6) g'olib va uning ovozini kortejga yig'ing, so'ng kortejni ochib (nom, son = ...) chiqaring.

Kutilgan natija:
Nomzodlar: ['Ali', 'Hasan', 'Vali']
Natija: {'Ali': 3, 'Vali': 2, 'Hasan': 1}
Eng ko'p ovoz: 3
Jami ovozlar: 6
Tekshiruv: True
G'olib: Ali — 3 ovoz
