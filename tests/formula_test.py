print(
    eval("A or (B and C)", __locals={'A': True})
)