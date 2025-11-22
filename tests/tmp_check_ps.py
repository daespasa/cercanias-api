try:
    import pydantic_settings
    print('pydantic_settings present', pydantic_settings.__version__)
except Exception as e:
    print('pydantic_settings import failed', e)
