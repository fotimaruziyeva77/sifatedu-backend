from typing import Any

from rest_framework import serializers

from .models import DailyTask, Entry

# Tanlovlar (OpenAPI'da nomli enum: `ENUM_NAME_OVERRIDES`).
PERIODS = [("week", "week"), ("month", "month"), ("all", "all")]
SCOPES = [("course", "course"), ("group", "group")]
DISCOUNTS = [("REFERRAL", "REFERRAL"), ("COUPON", "COUPON")]


class DailyTaskSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    kind = serializers.ChoiceField(choices=DailyTask.Kind.choices)
    title = serializers.CharField()
    done = serializers.BooleanField()
    url = serializers.CharField(
        help_text="Saytdagi sahifa (dars, vazifa, jadval) yoki bot havolasi."
    )


class RewardEntrySerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    reason = serializers.ChoiceField(choices=Entry.Reason.choices)
    xp = serializers.IntegerField(help_text="Hisoblangan XP (shtraf 0 dan pastga tushirmaydi).")
    coins = serializers.IntegerField()
    note = serializers.CharField()
    course_title = serializers.CharField()
    created_at = serializers.DateTimeField()
    penalty = serializers.BooleanField()
    canceled = serializers.BooleanField()
    cancel_reason = serializers.CharField()


class CouponSerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    percent = serializers.IntegerField()
    created_at = serializers.DateTimeField()
    reserved = serializers.BooleanField(help_text="To'lov kutilayotgan buyurtmaga biriktirilgan.")


class RulesSerializer(serializers.Serializer[dict[str, Any]]):
    """Admin'dagi qiymatlar: kabinetda "qanday topiladi" jadvali uchun."""

    lesson_xp = serializers.IntegerField()
    quiz_xp = serializers.IntegerField()
    homework_xp = serializers.IntegerField()
    attendance_xp = serializers.IntegerField()
    exam_xp = serializers.IntegerField()
    daily_bonus_xp = serializers.IntegerField()
    daily_missed_penalty = serializers.IntegerField()
    absent_penalty = serializers.IntegerField()
    late_penalty = serializers.IntegerField()
    homework_late_penalty = serializers.IntegerField()
    referral_lesson_coins = serializers.IntegerField()
    referral_paid_coins = serializers.IntegerField()
    referral_discount = serializers.IntegerField()
    coupon_percent = serializers.IntegerField()


class RewardsSerializer(serializers.Serializer[dict[str, Any]]):
    xp = serializers.IntegerField()
    coins = serializers.IntegerField()
    streak = serializers.IntegerField()
    best_streak = serializers.IntegerField()
    hidden = serializers.BooleanField()
    tasks = DailyTaskSerializer(many=True)
    coupons = CouponSerializer(many=True)
    history = RewardEntrySerializer(many=True)
    invite_url = serializers.CharField(help_text="Do'stni taklif qilish: saytdagi shaxsiy havola.")
    invite_bot_url = serializers.CharField(
        help_text="Botdagi shaxsiy havola (bot sozlanmagan — bo'sh)."
    )
    invited = serializers.IntegerField(help_text="Taklif qilinib ro'yxatdan o'tganlar.")
    rules = RulesSerializer()


class RewardHistorySerializer(serializers.Serializer[dict[str, Any]]):
    results = RewardEntrySerializer(many=True)
    next_page = serializers.IntegerField(allow_null=True)


class RewardSettingsSerializer(serializers.Serializer[dict[str, Any]]):
    hidden = serializers.BooleanField()


class RatingScopeSerializer(serializers.Serializer[dict[str, Any]]):
    kind = serializers.ChoiceField(choices=SCOPES)
    id = serializers.IntegerField()
    title = serializers.CharField()


class RatingPlaceSerializer(serializers.Serializer[dict[str, Any]]):
    place = serializers.IntegerField()
    name = serializers.CharField()
    xp = serializers.IntegerField()
    me = serializers.BooleanField()


class RatingMeSerializer(serializers.Serializer[dict[str, Any]]):
    place = serializers.IntegerField(allow_null=True)
    xp = serializers.IntegerField()
    hidden = serializers.BooleanField()


class RatingSerializer(serializers.Serializer[dict[str, Any]]):
    period = serializers.ChoiceField(choices=PERIODS)
    scope = serializers.CharField(allow_blank=True)
    scope_id = serializers.IntegerField(allow_null=True)
    total = serializers.IntegerField()
    top = RatingPlaceSerializer(many=True)
    me = RatingMeSerializer(allow_null=True)
    scopes = RatingScopeSerializer(many=True)


class DiscountSerializer(serializers.Serializer[dict[str, Any]]):
    percent = serializers.IntegerField()
    reason = serializers.ChoiceField(choices=DISCOUNTS)


class DiscountStateSerializer(serializers.Serializer[dict[str, Any]]):
    discount = DiscountSerializer(allow_null=True)


class PenaltySerializer(serializers.Serializer[dict[str, Any]]):
    id = serializers.IntegerField()
    student_id = serializers.IntegerField()
    student_name = serializers.CharField()
    reason = serializers.ChoiceField(choices=Entry.Reason.choices)
    xp = serializers.IntegerField()
    note = serializers.CharField()
    created_at = serializers.DateTimeField()
    canceled = serializers.BooleanField()
    cancel_reason = serializers.CharField()
    can_cancel = serializers.BooleanField()


class PenaltyCancelSerializer(serializers.Serializer[dict[str, Any]]):
    reason = serializers.CharField(max_length=300)
