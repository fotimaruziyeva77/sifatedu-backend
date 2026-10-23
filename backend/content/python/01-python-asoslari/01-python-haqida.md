+++
title = "1-mavzu: Python haqida, sintaktik xatolar, arifmetik amallar, print()"
summary = "Python nima, birinchi dastur, print(), arifmetik amallar va xato xabarlarini o'qish"
+++

::: slaydlar

###### Python darsi · 1-mavzu
# Python bilan tanishuv

Birinchi dastur, print(), arifmetik amallar va birinchi xatolar

`print("Salom!")` `7 // 2` nazariya + 3 ta amaliyot + viktorina

---

###### Bugungi reja
## Darsda nimalarni o'rganamiz?

### 01 Python

Nima u, qayerda ishlatiladi, qanday o'rnatiladi

### 02 print()

Birinchi dastur, sep va end

### 03 Arifmetika

`+ - * / // % **` va amallar tartibi

### 04 Xatolar

Xato xabarini o'qish va tuzatish

---

###### 01 · Muammo
## Kompyuter odam tilini tushunmaydi

### Odam tilida {.qizil}

«Ekranga salom deb yoz, keyin 25 ni 4 ga ko'paytirib ko'rsat»

Kompyuter buni bajara olmaydi: unga aniq buyruq kerak.

|||

### Python tilida {.sariq}

```python
print("Salom")
print(25 * 4)
```

Har bir qator — aniq buyruq. Python ularni yuqoridan pastga bajaradi.

---

###### 01 · Python
## Python qayerda ishlatiladi?

### Saytlar

Sayt va ilovalarning server qismi: Django, FastAPI

### Sun'iy intellekt

Ma'lumotlar tahlili, neyron tarmoqlar, AI xizmatlar

### Telegram botlar

Buyurtma, savol-javob va to'lov botlari

### Avtomatlashtirish

Excel, fayllar va hisobotlar bilan ishni tezlatish

***

> Birinchi til uchun eng qulayi: sodda yoziladi, bepul, o'rganish uchun materiallar juda ko'p.

---

###### 01 · Python
## Ish joyini tayyorlaymiz

### 01 Python

python.org dan o'rnating, «Add python.exe to PATH» belgisini qo'ying

### 02 VS Code

Muharrirni va uning Python kengaytmasini o'rnating

### 03 salom.py

Yangi fayl oching: nomi doim `.py` bilan tugaydi

### 04 Ishga tushirish

Run tugmasi yoki terminalda `python salom.py`

---

###### 02 · print()
## Birinchi dastur: print()

#### Kod

```python
print("Salom, dunyo!")
print(2026)
print("Ism:", "Ali")
print("2 + 3 =", 2 + 3)
```

|||

#### Ekranda

```text
Salom, dunyo!
2026
Ism: Ali
2 + 3 = 5
```

Matn qo'shtirnoqda, son — qo'shtirnoqsiz. Vergul qiymatlar orasiga bo'sh joy qo'yadi.

---

###### 02 · print()
## sep va end: chiqishni boshqaramiz

#### Kod

```python
print("A", "B", "C")
print("A", "B", "C", sep="-")
print(2026, 10, 23, sep=".")
print("Bir", end=" ")
print("qatorda")
```

|||

#### Ekranda

```text
A B C
A-B-C
2026.10.23
Bir qatorda
```

**sep** — qiymatlar orasidagi belgi (odatda bo'sh joy). **end** — qator oxiri (odatda yangi qator).

---

###### 03 · Arifmetika
## Arifmetik amallar

| Amal | Belgi | Misol | Natija |
|---|---|---|---|
| Qo'shish | `+` | `7 + 2` | `9` |
| Ayirish | `-` | `7 - 2` | `5` |
| Ko'paytirish | `*` | `7 * 2` | `14` |
| Bo'lish | `/` | `7 / 2` | `3.5` |
| Butun bo'lish | `//` | `7 // 2` | `3` |
| Qoldiq | `%` | `7 % 2` | `1` |
| Daraja | `**` | `7 ** 2` | `49` |

---

###### 03 · Arifmetika
## Bo'lishning uch turi

```python
print(17 / 5)    # 3.4
print(17 // 5)   # 3
print(17 % 5)    # 2
print(10 / 2)    # 5.0
```

|||

### / — oddiy bo'lish

Natija doim kasr son: `10 / 2` → `5.0`

### // — butun qism

Kasr qismi tashlab yuboriladi

### % — qoldiq

17 = 5 × 3 + 2, qoldiq — 2

---

###### 03 · Arifmetika
## Amallar tartibi

### 01 Qavs

```python
(2 + 3) * 4    # 20
```

### 02 Daraja

```python
2 ** 3 * 2     # 16
```

### 03 Ko'paytirish va bo'lish

```python
2 + 3 * 4      # 14
```

### 04 Qo'shish va ayirish

```python
10 - 4 - 3     # 3
```

***

> Teng darajali amallar chapdan o'ngga bajariladi. Shubha bo'lsa — qavs qo'ying, kod ham o'qilishi oson bo'ladi.

---

###### 03 · Arifmetika
## Hayotiy misol: nechta non olamiz?

#### Kod

```python
# 125 000 so'm bor, bitta non — 9 000 so'm
print(125000 // 9000)   # 13
print(125000 % 9000)    # 8000
```

|||

#### Ekranda

```text
13
8000
```

13 ta non olamiz va 8 000 so'm qoladi: 125 000 = 9 000 × 13 + 8 000.

---

###### Amaliyot 1 · 10 daqiqa
## Kalkulyator

1. Ismingiz va yoshingizni **bitta** `print()` bilan chiqaring.
2. Bir haftada necha daqiqa bor? Hisoblashni kod qilsin: `7 * 24 * 60`.
3. 1000 so'mni 3 kishiga bo'ling: har biriga qancha tegadi va qancha ortadi? (`//` va `%`)
4. 2 ning 10-darajasini va 15 ning kvadratini chiqaring (`**`).

> **Yulduzli topshiriq:** yoshingizni kunlarda hisoblang (yosh × 365) va «Men 6205 kun yashadim» ko'rinishida chiqaring.

---

###### 04 · Xatolar
# Xato — dushman emas, yo'l ko'rsatkich

Python xato qayerda va nima uchun ekanini o'zi aytib beradi.

`SyntaxError` `NameError` `ZeroDivisionError`

---

###### 04 · Xatolar
## Xato xabarini o'qish

```text
  File "salom.py", line 3
    print("Natija:" 5)
          ^^^^^^^^^^^
SyntaxError: invalid syntax. Perhaps you forgot a comma?
```

### 01 Qator raqami

`line 3` — xato shu qatorda

### 02 ^^^ belgisi

Aynan qaysi joyda ekanini ko'rsatadi

### 03 Oxirgi qator

Xato turi va maslahat: bu yerda vergul qolib ketgan

---

###### 04 · Xatolar
## Yangi boshlovchilarning 4 xatosi

### 1. Qo'shtirnoq yopilmagan

```diff
- print("Salom)     SyntaxError
+ print("Salom")
```

### 2. Katta harf

```diff
- Print("Salom")    NameError
+ print("Salom")
```

### 3. Nolga bo'lish

```diff
- print(10 / 0)     ZeroDivisionError
+ print(10 / 2)
```

### 4. O'zbekcha qo'shtirnoq

```diff
- print(«Salom»)    SyntaxError
+ print("Salom")
```

---

###### Amaliyot 2 · 10 daqiqa
## Xatolarni toping va tuzating

```python
# Bu kodda 4 ta xato bor
print("Bugun dars bor)
Print("Soat:", 14)
print("Natija" 5 + 5)
print(100 / 0)
```

1. Ishga tushiring va **birinchi** xato xabarini o'qing: qaysi qator, qanday xato?
2. Xatoni tuzating, yana ishga tushiring — keyingi xato chiqadi.
3. To'rttala xatoni tuzating: oxirgi qatorda 0 ga emas, 4 ga bo'ling.
4. Har bir xato turini daftarga yozing.

---

###### Amaliyot 3 · Mini loyiha · 15 daqiqa
## Do'kon cheki

#### Kod

```python
print("=" * 26)
print("     SIFAT DO'KONI")
print("=" * 26)
print("Non  2 x 4000  =", 2 * 4000)
print("Sut  1 x 12000 =", 1 * 12000)
print("-" * 26)
print("Jami:", 2 * 4000 + 12000, "so'm")
```

|||

#### Endi o'zingiz davom ettiring

1. Chekka yana 2 ta mahsulot qo'shing.
2. Jami summani qayta hisoblang.
3. Xaridor 50 000 so'm berdi: qaytimni chiqaring.
4. Oxiriga «Xaridingiz uchun rahmat!» yozing.

---

###### 05 · Viktorina
## Kompyutersiz ayting: ekranda nima chiqadi?

### 1-savol

```python
print(3 + 2 * 5)
```

### 2-savol

```python
print(20 / 4)
```

### 3-savol

```python
print(23 % 5)
```

### 4-savol

```python
print(2 ** 3)
```

### 5-savol

```python
print("A", "B", sep="/")
```

### 6-savol

```python
print("Ha" * 3)
```

---

###### 05 · Viktorina
## Javoblar: nechta to'g'ri topdingiz?

### 1-savol

`13`

Avval ko'paytirish: 2 × 5 = 10, keyin 3 + 10.

### 2-savol

`5.0`

`/` doim kasr son beradi.

### 3-savol

`3`

23 = 5 × 4 + 3, qoldiq — 3.

### 4-savol

`8`

2 × 2 × 2 = 8.

### 5-savol

`A/B`

`sep` qiymatlar orasiga qo'yiladi.

### 6-savol

`HaHaHa`

Matn songa ko'paytirilsa, takrorlanadi.

---

###### Xulosa va uyga vazifa
## Bugun nimani o'rgandik

### Esda qoladigan 4 narsa {.sariq}

- `print()` ekranga chiqaradi: `sep` va `end` bilan boshqariladi
- `/` — kasr natija, `//` — butun qism, `%` — qoldiq
- Tartib: qavs → `**` → `* / // %` → `+ -`
- Xato xabarini oxirgi qatoridan o'qing

|||

### Uyga vazifa {.qizil}

1. Vizitka: `"*" * 25` chiziqlari bilan
2. Kalkulyator: 17 va 5 ustida 7 ta amal
3. Vaqt: sutkadagi soniya, haftadagi daqiqa
4. Do'kon: nechta daftar va qancha qoladi
5. Uchta xatoni tuzatish

Batafsil — platformadagi «Uy vazifasi» bo'limida.

::: ustozga

Dars rejasi (2 soat):
- 0–10 daq: tanishuv; 1–4-slaydlar. O'quvchilardan Python bilan nima qilmoqchi ekanini so'rang.
- 10–30 daq: 5-slayd — Python va VS Code o'rnatilganini tekshiring. «Add python.exe to PATH» belgisi qo'yilmagan bo'lsa, terminalda python buyrug'i ishlamaydi — qayta o'rnatish kerak.
- 30–55 daq: print() va arifmetika (6–11-slaydlar). Har misolni o'quvchi o'z kompyuterida yozsin, faqat ekranga qarab o'tirmasin.
- 55–65 daq: Amaliyot 1.
- 65–75 daq: tanaffus.
- 75–95 daq: xatolar (13–16-slaydlar). Ataylab xato yozing va xabarni birga o'qing — darsning eng muhim qismi. Amaliyot 2 shu yerda.
- 95–110 daq: Amaliyot 3 (mini loyiha) — tez bajarganlarga qaytimni hisoblash.
- 110–120 daq: viktorina (og'zaki), platformadagi test va uy vazifasini tushuntirish.

Ko'p uchraydigan xatolar: o'zbekcha qo'shtirnoq «» yoki ‘ ’ belgisi (Python faqat " va ' ni tushunadi), Print katta harf bilan, qavs yopilmagan, qator boshida ortiqcha bo'sh joy (IndentationError), kod Word'dan nusxalanganda belgilar buzilishi.

::: test

? Python dasturi fayli qaysi kengaytma bilan saqlanadi?
+ .py
- .pt
- .python
- .txt

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(2 + 3 * 4)
```
= 14
> Avval ko'paytirish: 3 * 4 = 12, keyin qo'shish: 2 + 12 = 14.

? Quyidagi kod nima chiqaradi?
```python
print((2 + 3) * 4)
```
+ 20
- 14
- 24
- 9
> Qavs ichidagi amal birinchi bajariladi: (2 + 3) = 5, 5 * 4 = 20.

? Quyidagi kod nima chiqaradi?
```python
print(15 / 4)
```
+ 3.75
- 3
- 3.7
- 4
> / — oddiy bo'lish, natija doim haqiqiy son (float).

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(15 // 4)
```
= 3
> // — butun bo'lish: kasr qismi tashlab yuboriladi.

? Quyidagi kod nima chiqaradi?
```python
print(15 % 4)
```
+ 3
- 3.75
- 1
- 4
> % — qoldiq: 15 = 4 * 3 + 3.

? Quyidagi kod nima chiqaradi? Javobni yozing.
```python
print(2 ** 4)
```
= 16
> ** — darajaga ko'tarish: 2 * 2 * 2 * 2 = 16.

? Quyidagi kod nima chiqaradi?
```python
print("Salom", "dunyo")
```
+ Salom dunyo
- Salomdunyo
- Salom,dunyo
- "Salom" "dunyo"
> print() qiymatlar orasiga standart holatda bitta bo'sh joy qo'yadi.

? Quyidagi kod nima chiqaradi?
```python
print("A", "B", sep="-")
```
+ A-B
- A B
- AB
- A - B
> sep — qiymatlar orasiga qo'yiladigan belgi.

? Quyidagi kod nima chiqaradi?
```python
print("Python" * 3)
```
+ PythonPythonPython
- Python 3
- Python*3
- Xato beradi
> Matnni songa ko'paytirsa, matn shuncha marta takrorlanadi.

? Qaysi qator SyntaxError beradi?
+ print("Salom')
- print("Salom")
- print('Salom')
- print("Salom", 5)
> Qo'shtirnoq bir xil bo'lishi kerak: " bilan ochilgan matn " bilan yopiladi.

? Python'da izoh (kommentariya) qaysi belgi bilan yoziladi?
+ #
- //
- /* */
- --
> # dan keyingi matnni Python bajarmaydi.

? Quyidagi kod nima chiqaradi?
```python
print(10 / 2)
```
+ 5.0
- 5
- 5.00
- 2
> / har doim float qaytaradi, natija butun bo'lsa ham.

? Qaysilari arifmetik operator? Hammasini belgilang.
+ **
+ %
+ //
- ==
- and
> == — taqqoslash, and — mantiqiy operator.

::: uy-vazifasi

5 ta topshiriq — hammasini bitta kodda yuboring: pastdagi «Kod» maydoniga qo'ying (yoki .py fayl biriktiring). Har topshiriq oldidan izoh yozing: # 1-topshiriq, # 2-topshiriq va h.k.
Yuborishdan oldin kodni ishga tushirib, natijani «Kutilgan natija» bilan solishtiring.

1-topshiriq. Vizitka
print() bilan quyidagi vizitkani chiqaring (o'z ismingizni yozing). Yulduzchalar chizig'ini "*" * 25 bilan yasang.

Kutilgan natija:
*************************
Ism: Ali Valiyev
Kurs: Python asoslari
Shahar: Navoiy
*************************

2-topshiriq. Kalkulyator
17 va 5 sonlari ustida hamma arifmetik amallarni bajaring. Har qatorni print(17, "+", 5, "=", 17 + 5) ko'rinishida chiqaring.

Kutilgan natija:
17 + 5 = 22
17 - 5 = 12
17 * 5 = 85
17 / 5 = 3.4
17 // 5 = 3
17 % 5 = 2
17 ** 5 = 1419857

3-topshiriq. Vaqt
Bir sutkada necha soniya va bir haftada necha daqiqa borligini hisoblab chiqaring (javobni qo'lda yozmang — hisoblashni kod qilsin).

Kutilgan natija:
86400
10080

4-topshiriq. Do'kon
50 000 so'm bor, bitta daftar 7 000 so'm. Nechta daftar olish mumkin va qancha pul qoladi? // va % dan foydalaning.

Kutilgan natija:
7
1000

5-topshiriq. Xatoni tuzating
Quyidagi kodda 3 ta xato bor. Tuzating: oxirgi qatorda nolga emas, 2 ga bo'ling.

print("Salom dunyo)
Print("Ikki")
print(10 / 0)

Kutilgan natija:
Salom dunyo
Ikki
5.0
