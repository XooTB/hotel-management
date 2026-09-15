from django.conf import settings


def hotel(request):
    return {
        "HOTEL_NAME": settings.HOTEL_NAME,
        "CURRENCY": settings.HOTEL_CURRENCY,
        "CHECK_IN_TIME": settings.HOTEL_CHECK_IN_TIME,
        "CHECK_OUT_TIME": settings.HOTEL_CHECK_OUT_TIME,
    }
