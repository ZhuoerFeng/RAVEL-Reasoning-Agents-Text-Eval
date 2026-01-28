
## Cloze

```json
{
  "infer_id": "A unique string identifier for the specific inference example (e.g., 'cloze_en_3').",
  "task_type": "The high-level category of the NLP task, in this case, 'cloze' (fill-in-the-blank).",
  "sub_task": "The specific domain or genre of the text being processed, such as 'fiction'.",
  "instruction": "The natural language directive or prompt that tells the model how to perform the task.",
  "input": {
    "content": "The text appearing immediately before the gap that needs to be filled. The PREFIX + [fill in the blank] + SUFFIX are already in it",
  },
  "reference": "The ground-truth or 'gold standard' text that represents the missing content between the prefix and suffix."
}
```



## Condition


```json
{
  "infer_id": "A unique string identifier for the inference task instance (e.g., 'condition_en_0').",
  "task_type": "The high-level category of the NLP task, here 'condition' (constrained generation).",
  "sub_task": "The specific domain or style of the content, in this case, 'academic_writing'.",
  "instruction": "The primary prompt or directive given to the model, detailing the essay's structure, key concepts to cover, and stylistic requirements.",
  "input": {
    "outline": "A detailed set of structural and content-specific constraints that the generated text must follow.",
  },
  "reference": "The ground-truth or exemplar essay that fulfills all the criteria and constraints specified in the instructions and input attributes."
}
```

## Edit

```json
{
  "infer_id": "A unique identifier for the specific editing task instance (e.g., 'edit_en_60').",
  "task_type": "The high-level category of the NLP task, here 'edit' (refining or rewriting existing text).",
  "sub_task": "The specific genre or format of the text being edited, such as 'essay' or academic summary.",
  "instruction": "A detailed prompt outlining the specific goals for the rewrite, including quality of expression, logic, imagery, and emotional tension.",
  "input": {
    "content": "The original draft text that requires improvement or correction.",
    "critique": "A comprehensive professional evaluation identifying specific weaknesses in the draft (e.g., conceptual errors, logical gaps) and providing actionable revision advice."
  },
  "reference": "The factual source material or background information used to ensure the rewritten version remains accurate and grounded in evidence."
}
```

## End2end

```json
{
  "infer_id": "A unique identifier for the specific generation task instance (e.g., 'end2end_en_1').",
  "task_type": "The high-level category of the NLP task, here 'end2end' (complete generation from prompt to final output).",
  "sub_task": "The specific domain or genre of the writing, in this case, 'academic_writing'.",
  "instruction": "The comprehensive user prompt detailing the essay's subject (water), specific scientific parameters to include (molecular structure, symmetry, acid-base behavior), and the desired length and style.",
  "input": {
    "genre": "The specific format of the output, identifying it as an 'academic/analytical essay'.",
    "brief": "A concise summary of the core scientific themes the essay must address.",
    "audience": "The intended readership (students), which determines the technical level, tone, and complexity of the language.",
    "word": "The target word count for the generated content (e.g., 800 words)."
  },
  "reference": "A 'gold standard' academic essay that fulfills all the prompt's requirements, including citations and structural elements like figure placeholders and a bibliography."
}
```


