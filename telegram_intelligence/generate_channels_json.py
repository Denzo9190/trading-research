import json

def generate_channels_from_file(input_file='channels_raw.txt', output_file='channels.json'):
    identifiers = []
    with open(input_file, 'r', encoding='utf-8') as f:
        # Пропускаем заголовок
        next(f)
        for line in f:
            line = line.strip()
            if not line:
                continue
            # Разделяем по табуляции
            parts = line.split('\t')
            if len(parts) >= 3:
                identifier = parts[2].strip()  # третий столбец — идентификатор для channels.json
                identifiers.append(identifier)

    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(identifiers, f, ensure_ascii=False, indent=4)

    print(f"Сгенерирован {output_file} с {len(identifiers)} каналами.")

if __name__ == '__main__':
    generate_channels_from_file()
