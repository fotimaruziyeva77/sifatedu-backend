+++
title = "6-mavzu: ro'yxat (list) bilan tanishuv"
summary = "Ro'yxat yaratish, indeks va kesish, append/insert/remove/pop, saralash va asosiy funksiyalar"
+++

::: slaydlar

###### Python darsi · 6-mavzu
# Ro'yxat (list)

Ko'p ma'lumotni bitta o'zgaruvchida saqlashni o'rganamiz

`[ "olma", "anor" ]` `a.append(x)` nazariya + 3 ta amaliyot + viktorina

---

###### Bugungi reja
## Darsda nimalarni o'rganamiz?

### 01 Ro'yxat

Yaratish, indeks, kesish va `len()`

### 02 O'zgartirish

`append`, `insert`, `remove`, `pop`

### 03 Saralash

`sort()`, `sorted()`, kamayish tartibi

### 04 Asboblar

`in`, `count`, `index`, `min`, `max`, `sum`

---

###### 01 · Muammo
## Sinfda 30 o'quvchi bor. 30 ta o'zgaruvchi ochamizmi?

### Noqulay usul {.qizil}

```python
oquvchi1 = "Ali"
oquvchi2 = "Vali"
oquvchi3 = "Laylo"
oquvchi4 = "Sardor"
# ... yana 26 qator
```

|||

### Qulay usul: ro'yxat {.sariq}

```python
oquvchilar = ["Ali", "Vali",
    "Laylo", "Sardor"]
```

Bitta nom, ichida xohlagancha qiymat.

---

###### 02 · Ro'yxat
## List: tartibli va o'zgaruvchan ro'yxat

```python
mevalar = ["olma", "anor", "uzum"]
baholar = [5, 4, 5, 3]
aralash = ["Ali", 14, True, 4.5]
bosh = []

print(mevalar)
# ['olma', 'anor', 'uzum']
print(len(baholar))   # 4
```

|||

### Kvadrat qavs [ ]

Elementlar vergul bilan ajratiladi.

### Har xil tur

Matn, son, True/False birga turishi mumkin.

### Tartib saqlanadi

Qanday yozsangiz, shunday turadi.

---

###### 02 · Ro'yxat
## Indeks: sanoq 0 dan boshlanadi

```indeks
mevalar = ["olma", "anor", "uzum", "nok", "behi"]
```

```python
mevalar = ["olma", "anor", "uzum", "nok", "behi"]
mevalar[0]     # 'olma' — birinchi element
mevalar[-1]    # 'behi' — oxirgi element
mevalar[5]     # IndexError: bunday indeks yo'q
```

---

###### 02 · Ro'yxat
## Kesish: ro'yxatdan bo'lak olish

```python
sonlar = [10, 20, 30, 40, 50, 60]
sonlar[1:4]     # [20, 30, 40]
sonlar[:3]      # [10, 20, 30]
sonlar[3:]      # [40, 50, 60]
sonlar[::2]     # [10, 30, 50]
sonlar[::-1]    # [60, 50, 40, 30, 20, 10]
```

|||

### [boshi : oxiri : qadam]

Boshi kiradi, oxiri kirmaydi — matndagidek.

### Asl ro'yxat o'zgarmaydi

Kesish har doim yangi ro'yxat qaytaradi.

---

###### 03 · O'zgartirish
## Listni o'zgartirish mumkin

`mevalar = ["olma", "anor"]`

| Amal | Kod | Ro'yxat holati |
|---|---|---|
| Almashtirish | `mevalar[0] = "nok"` | `['nok', 'anor']` |
| Oxiriga qo'shish | `mevalar.append("uzum")` | `['nok', 'anor', 'uzum']` |
| O'rtaga qo'shish | `mevalar.insert(1, "behi")` | `['nok', 'behi', 'anor', 'uzum']` |
| Qiymat bo'yicha | `mevalar.remove("anor")` | `['nok', 'behi', 'uzum']` |
| Oxirgisini olish | `mevalar.pop()` | `['nok', 'behi']` |

**pop()** o'chirilgan elementni qaytaradi: bu yerda 'uzum'. **remove()** faqat birinchi uchraganini o'chiradi.

---

###### 03 · O'zgartirish
## Qo'shish, birlashtirish, o'chirish

#### Kod

```python
a = [1, 2, 3]
a.append(4)
print(a)
a.insert(0, 9)
print(a)
print(a + [5, 6])
x = a.pop()
print(x, a)
del a[0]
print(a)
```

|||

#### Ekranda

```text
[1, 2, 3, 4]
[9, 1, 2, 3, 4]
[9, 1, 2, 3, 4, 5, 6]
4 [9, 1, 2, 3]
[1, 2, 3]
```

`a + b` — yangi ro'yxat, `a` o'zgarmaydi. `del a[0]` — indeks bo'yicha o'chiradi.

---

###### Amaliyot 1 · 10 daqiqa
## Do'stlar ro'yxati

1. 5 ta do'stingiz ismidan **dostlar** ro'yxatini tuzing va ekranga chiqaring.
2. Indeks yordamida birinchi va oxirgi ismni alohida chiqaring.
3. Yangi do'st qo'shing (**append**), bittasini o'chiring (**remove**).
4. Alifbo tartibida saralang (**sort**) va ro'yxatni chiqaring.

> **Yulduzli topshiriq:** baholar = [5, 4, 3, 5, 4] ro'yxatining o'rtacha bahosini hisoblang.

---

###### 04 · Saralash va asboblar
# Ro'yxat bilan ishlash asboblari

Saralash, qidirish va hisoblash — bitta qatorda.

`sort()` `in` `count()` `sum()`

---

###### 04 · Saralash va asboblar
## sort() va sorted(): saralash

```python
a = [5, 3, 8, 1]
a.sort()
print(a)              # [1, 3, 5, 8]
a.sort(reverse=True)
print(a)              # [8, 5, 3, 1]
b = [3, 1, 2]
print(sorted(b))      # [1, 2, 3]
print(b)              # [3, 1, 2]
```

|||

### sort()

Ro'yxatning o'zini saralaydi

### sorted()

Yangi saralangan ro'yxat beradi, asli o'zgarmaydi

### reverse=True

Kamayish tartibida

---

###### 04 · Saralash va asboblar
## Har kuni kerak bo'ladigan 6 ta asbob

`b = [4, 5, 3, 5]`

### Uzunlik

```python
len(b)        # 4
```

### Yig'indi, eng katta

```python
sum(b)        # 17
max(b)        # 5
```

### Bormi?

```python
3 in b        # True
2 in b        # False
```

### Necha marta?

```python
b.count(5)    # 2
```

### Qayerda?

```python
b.index(3)    # 2
```

### Saralash

```python
b.sort()
b             # [3, 4, 5, 5]
```

---

###### 04 · Saralash va asboblar
## Matn va ro'yxat: split, join, list

#### Kod

```python
s = "olma,anor,nok"
mevalar = s.split(",")
print(mevalar)
print(", ".join(mevalar))
print(list("salom"))
```

|||

#### Ekranda

```text
['olma', 'anor', 'nok']
olma, anor, nok
['s', 'a', 'l', 'o', 'm']
```

`split` — matndan ro'yxat, `join` — ro'yxatdan matn.

---

###### 04 · Saralash va asboblar
## Diqqat: ro'yxatdagi 4 tuzoq

### 1. sort() natija qaytarmaydi

```diff
- b = a.sort()       b → None
+ a.sort()
```

### 2. Yo'q indeks

```diff
- a[3]  # [1, 2, 3]  IndexError
+ a[-1]              oxirgisi
```

### 3. Yo'q elementni o'chirish

```diff
- a.remove(7)        ValueError
+ if 7 in a: a.remove(7)
```

### 4. Nusxa emas, o'sha ro'yxat

```diff
- b = a              ikkalasi bitta
+ b = a.copy()
```

---

###### Amaliyot 2 · 10 daqiqa
## Xarid ro'yxati

1. Bo'sh `xaridlar` ro'yxatini yarating.
2. `input()` bilan 3 ta mahsulot so'rab, ro'yxatga qo'shing (`append`).
3. Ro'yxatda "non" bormi — tekshiring (`in`).
4. Mahsulotlar sonini va saralangan ro'yxatni chiqaring.

> **Yulduzli topshiriq:** eng uzun nomli mahsulotni toping: `max(xaridlar, key=len)`.

---

###### Amaliyot 3 · Mini loyiha · 15 daqiqa
## Baholar jurnali

#### Kod

```python
baholar = []
baholar.append(int(input("1-baho: ")))
baholar.append(int(input("2-baho: ")))
baholar.append(int(input("3-baho: ")))
print("Baholar:", baholar)
orta = sum(baholar) / len(baholar)
print("O'rtacha:", round(orta, 1))
print("Eng yuqori:", max(baholar))
```

|||

#### Endi o'zingiz davom ettiring

1. 5 ta baho so'rang.
2. 5 lar sonini chiqaring (`count`).
3. Eng past bahoni o'chirib, o'rtachani qayta hisoblang.
4. O'rtacha 4.5 dan yuqori bo'lsa — «A'lochi!» deng.

---

###### 05 · Viktorina
## Kompyutersiz ayting: ekranda nima chiqadi?

### 1-savol

```python
a = [1, 2, 3]
a.append(4)
print(len(a))
```

### 2-savol

```python
a = [10, 20, 30]
print(a[-1])
```

### 3-savol

```python
s = [5, 1, 4]
s.sort()
print(s[0])
```

### 4-savol

```python
m = ["a", "b", "c", "d"]
print(m[1:3])
```

### 5-savol

```python
a = [1, 2, 3]
a[1] = 20
print(a)
```

### 6-savol

```python
a = [4, 4, 5]
print(a.count(4))
```

---

###### 05 · Viktorina
## Javoblar: nechta to'g'ri topdingiz?

### 1-savol

`4`

3 ta edi, append bittasini qo'shdi.

### 2-savol

`30`

-1 har doim oxirgi element.

### 3-savol

`1`

Saralangach [1, 4, 5] bo'ladi.

### 4-savol

`['b', 'c']`

1 kiradi, 3 kirmaydi.

### 5-savol

`[1, 20, 3]`

1-indeksdagi element almashdi.

### 6-savol

`2`

4 ikki marta uchraydi.

---

###### Xulosa va uyga vazifa
## Bugun nimani o'rgandik

### Esda qoladigan 4 narsa {.sariq}

- List `[ ]` — tartibli va o'zgaruvchan
- Indeks 0 dan, oxirgisi `-1`; kesishda oxiri kirmaydi
- `append` — oxiriga, `insert` — o'rtaga, `remove`/`pop` — o'chiradi
- `sort()` o'zini saralaydi, `sorted()` yangisini beradi

|||

### Uyga vazifa {.qizil}

1. Baholar statistikasi
2. Xarid ro'yxati: `append`, `insert`, `remove`
3. Saralash va eng katta 2 tasi
4. Shaharlar: `in` va `index`
5. Kesishlar

Batafsil — platformadagi «Uy vazifasi» bo'limida.

::: ustozga

Dars rejasi (2 soat):
- 0–15 daq: 5-dars uy vazifasi (if / elif, kabisa yili).
- 15–35 daq: ro'yxat, indeks va kesish (3–6-slaydlar). Indeks sxemasini doskada chizing — matndagi indeks bilan bir xil ekanini ko'rsating.
- 35–50 daq: o'zgartirish (7–8-slaydlar). Har amaldan keyin ro'yxat holatini o'quvchilar taxmin qilsin.
- 50–60 daq: Amaliyot 1.
- 60–70 daq: tanaffus.
- 70–90 daq: saralash va asboblar, tuzoqlar (10–14-slaydlar). b = a.sort() xatosini jonli ko'rsating.
- 90–110 daq: Amaliyot 2 va 3.
- 110–120 daq: viktorina, platformadagi test va uy vazifasi.

Ko'p uchraydigan xatolar: indeksni 1 dan sanash; a = a.sort() (natija None); remove'ga indeks berish (remove qiymat oladi, del/pop — indeks); yo'q elementni remove qilish (ValueError); b = a deb nusxa olgandek o'ylash.

::: test

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
sonlar = [10, 20, 30]
print(sonlar[0])
```
= 10
> Indeks 0 dan boshlanadi.

? Quyidagi kod nima chiqaradi?
```python
sonlar = [10, 20, 30]
print(sonlar[-1])
```
+ 30
- 10
- 20
- Xato beradi
> -1 — oxirgi element.

? Quyidagi kod nima chiqaradi?
```python
a = [1, 2, 3]
a.append(4)
print(a)
```
+ [1, 2, 3, 4]
- [4, 1, 2, 3]
- [1, 2, 3]
- 4

? Quyidagi kod nima chiqaradi?
```python
a = [5, 3, 8]
a.sort()
print(a)
```
+ [3, 5, 8]
- [8, 5, 3]
- [5, 3, 8]
- None
> sort() ro'yxatni o'sish tartibida saralaydi.

? Quyidagi kod nima chiqaradi?
```python
a = [1, 2, 3]
a.insert(0, 9)
print(a)
```
+ [9, 1, 2, 3]
- [1, 2, 3, 9]
- [1, 9, 2, 3]
- [9]
> insert(0, 9) — 0-o'ringa 9 ni qo'yadi.

? Quyidagi kod nima chiqaradi?
```python
a = ["olma", "anor"]
a.remove("olma")
print(a)
```
+ ['anor']
- ['olma']
- []
- ['olma', 'anor']

? Quyidagi kod nima chiqaradi?
```python
a = [1, 2, 3, 4, 5]
print(a[1:3])
```
+ [2, 3]
- [1, 2, 3]
- [2, 3, 4]
- [1, 2]
> Kesim [1:3] — 1 va 2-indekslar (3 kirmaydi).

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
a = [3, 1, 2]
print(len(a) + a[0])
```
= 6
> len(a) = 3, a[0] = 3, jami 6.

? Quyidagi kod nima chiqaradi?
```python
a = [1, 2]
b = [3]
print(a + b)
```
+ [1, 2, 3]
- [4, 2]
- [[1, 2], [3]]
- Xato beradi
> Ikki ro'yxat qo'shilsa, ular birlashadi.

? Quyidagi kod nima chiqaradi?
```python
a = [7, 8, 9]
a.pop()
print(a)
```
+ [7, 8]
- [8, 9]
- [7, 8, 9]
- [9]
> pop() oxirgi elementni olib tashlaydi.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
a = [4, 4, 5]
print(a.count(4))
```
= 2

? Quyidagi kod nima chiqaradi?
```python
a = ["x", "y", "z"]
print(a.index("z"))
```
+ 2
- 3
- z
- 1

? Qaysi ifoda bo'sh ro'yxat yaratadi?
+ []
- {}
- ()
- ""
> {} — bo'sh lug'at (dict), () — bo'sh kortej (tuple), "" — bo'sh matn.

? Quyidagi kod nima chiqaradi?
```python
a = [1, 2, 3]
a[1] = 20
print(a)
```
+ [1, 20, 3]
- [20, 2, 3]
- [1, 2, 20]
- Xato beradi
> Ro'yxat elementini o'zgartirish mumkin.

::: uy-vazifasi

5 ta topshiriq — hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying (yoki .py fayl biriktiring). Har topshiriq oldidan izoh yozing: # 1-topshiriq, # 2-topshiriq va h.k.
Javoblarni qo'lda yozmang — hisoblashni kod qilsin.

1-topshiriq. Baholar statistikasi
baholar = [4, 5, 3, 5, 4]. Baholar soni, yig'indisi, o'rtachasi, eng yuqori va eng past bahoni, 5 lar sonini chiqaring.

Kutilgan natija:
Soni: 5
Yig'indi: 21
O'rtacha: 4.2
Eng yuqori: 5
Eng past: 3
5 lar soni: 2

2-topshiriq. Xarid ro'yxati
xaridlar = ["non", "sut"]. Oxiriga "tuxum" qo'shing (append), boshiga "choy" qo'shing (insert), "sut" ni o'chiring (remove). Ro'yxatni va uzunligini chiqaring.

Kutilgan natija:
['choy', 'non', 'tuxum']
3

3-topshiriq. Saralash
sonlar = [42, 7, 19, 88, 3]. O'sish tartibida, kamayish tartibida va eng katta 2 tasini (kesish bilan) chiqaring.

Kutilgan natija:
[3, 7, 19, 42, 88]
[88, 42, 19, 7, 3]
[88, 42]

4-topshiriq. Shaharlar
shaharlar = ["Toshkent", "Buxoro", "Navoiy", "Samarqand"]. "Navoiy" ro'yxatda bormi (in), uning indeksi (index) va Navoiy bilan oxirgi shaharni bitta print bilan chiqaring.

Kutilgan natija:
True
2
Navoiy Samarqand

5-topshiriq. Kesishlar
harflar = ["a", "b", "c", "d", "e", "f"]. Birinchi 3 tasi, oxirgi 2 tasi, juft indeksdagilar ([::2]) va teskari tartibda chiqaring.

Kutilgan natija:
['a', 'b', 'c']
['e', 'f']
['a', 'c', 'e']
['f', 'e', 'd', 'c', 'b', 'a']
