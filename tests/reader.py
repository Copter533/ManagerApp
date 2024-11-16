from transformers import pipeline, set_seed
generator = pipeline('text-generation', model='gpt2-large')
set_seed(142)

c = 0
for data in generator('Hi, I\'m an announcer from the Mood Workshop channel,', max_length=100, num_return_sequences=5):
    c += 1
    print(f'{c}. {data["generated_text"]}')
