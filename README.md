# LLMPlayplace

## embedding contextuels

- Unidirectionnel : seuls les mots précédents comptent (very good for answering question, bad for given summary of the article)
- Bidirectionnel : les mots avant et après comptent. (e.g. BERT) (very good for given summary of the article, bad for  answering question)

## LLM?

Un LLM, c’est un **réseau de neurones** qui est entraîné à résoudre une `tâche prétexte` sur un énorme corpus de texte.

- Next token prediction: (e.g GPT) : earth has ? (-> people, air, etc)
- Masked token prediction: toto (loves/hates/plays with) titi.

## workflow

1. tokinization
2. word embedding
3. 