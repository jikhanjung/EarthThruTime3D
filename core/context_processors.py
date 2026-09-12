from config.version import APP_NAME, COPYRIGHT_YEAR, RELEASE_DATE, VENDOR, VERSION


def branding(request):
    return {"app_name": APP_NAME, "vendor": VENDOR, "version": VERSION,
            "release_date": RELEASE_DATE, "copyright_year": COPYRIGHT_YEAR}
