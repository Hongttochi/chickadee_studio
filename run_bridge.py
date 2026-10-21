if __name__ == '__main__':
    import sys
    if '--ocr-worker' in sys.argv:
        from chickadee.ocr_worker import main
    else:
        from chickadee.bridge import main
    main()
