## 🌐 Получение API ключа OpenRouter

1. **Регистрация и вход**  
   - Перейдите на [OpenRouter](https://openrouter.ai/)  
   - Войдите через GitHub, Google или Email  
   - Если Email — подтвердите регистрацию через почту  

2. **Создание API ключа**  
   - Перейдите на страницу [Keys](https://openrouter.ai/keys)  
   - Нажмите **"Create Key"**, укажите название 
   - Скопируйте ключ **один раз** — он секретный!  

3. **Добавьте ключ в `.env`**  
```
OPENROUTER_API_KEY=<ваш_ключ>
```
4. **Выберите модель LLM и вставьте в `.env`**
```
LLM_MODEL=mistralai/mistral-7b-instruct:free
```

