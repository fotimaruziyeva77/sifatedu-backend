"""O'qish hodisalari: dars tugatildi, test o'tildi, vazifa topshirildi va h.k.

Sertifikat va XP shu hodisalarni tinglaydi — hodisa yuz bergan ilova ular haqida bilmaydi.
Hodisa tranzaksiya ichida yuboriladi; og'ir ishni tinglovchi `transaction.on_commit` bilan qiladi.
Barcha hodisalarda `user_id` va `course_id` bor.
"""

from django.dispatch import Signal

# lesson_id
lesson_completed = Signal()
# quiz_id, lesson_id, score, first — birinchi marta o'tildimi
quiz_passed = Signal()
# assignment_id, lesson_id, late
homework_submitted = Signal()
# assignment_id, lesson_id, score
homework_accepted = Signal()
# live_lesson_id, status (PRESENT/LATE/ABSENT/EXCUSED)
attendance_marked = Signal()
# exam_id, total, passed
exam_finalized = Signal()
# order — to'langan buyurtma (user_id va course_id yo'q: tinglovchi buyurtmadan oladi)
order_paid = Signal()
