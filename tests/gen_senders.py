def fi_numbers():
    n1, n2 = 1, 1
    while True:
        jump_to = yield n1
        if jump_to is None:
            n1, n2 = n1 + n2, n1
        else:
            n1, n2 = jump_to


fi_gen = fi_numbers()
print(next(fi_gen))
fi_gen.send((5, 8))
print(next(fi_gen))
print(next(fi_gen))
print(next(fi_gen))
print(next(fi_gen))