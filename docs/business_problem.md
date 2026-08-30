# Business problem

## Контекст

`AnswerFlow` — синтетический B2B SaaS для команд клиентской поддержки. Продукт создаёт AI
suggestions на основе базы знаний компании. Единица принятия продуктового решения —
`workspace`, потому что подписка, onboarding и rollout происходят на уровне команды.

## Решение, которое должна поддержать аналитика

Product Manager должен выбрать первый участок onboarding для улучшения и определить,
можно ли масштабировать guided onboarding без вреда качеству и unit economics.

## Главный вопрос

Какие действия days 0–7 связаны с формированием повторяемой командной ценности и где
находится addressable drop-off?

## Аудитория

- Product Manager — activation и experiment decision;
- Data/BI Lead — definitions, marts и качество данных;
- Finance — inference cost и contribution margin;
- Customer Success — сегменты с низкой team adoption.

## Scope Week 1

- core entities и event taxonomy;
- deterministic synthetic data;
- activation metric contract;
- activation mart;
- data-quality checks;
- starter notebook.

Retention, unit economics, полноценный эксперимент и DataLens следуют после устойчивого
vertical slice.
