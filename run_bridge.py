if __name__ == '__main__':
    import sys
    if '--content-worker' in sys.argv:
        from chickadee.content_worker import main
    elif '--laya-worker' in sys.argv:
        from chickadee.laya_worker import main
    elif '--ocr-worker' in sys.argv:
        from chickadee.ocr_worker import main
    else:
        from chickadee.bridge import main
    main()
