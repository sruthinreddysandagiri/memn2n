import tensorflow as tf
# import tensorflow_text as tf_text

from .hparams import *


def get_tokenizer_fn(hparams):

    # tf_word_tokenizer = tf_text.WhitespaceTokenizer()

    def word_tokenize(text):
        # return tf_word_tokenizer.tokenize(text)
        return tf.strings.split(text, sep=' ')

    def character_tokenize(text):
        return tf.strings.bytes_split(text)

    if hparams[HP_TOKEN_TYPE.name] == 'word':
        return word_tokenize
    elif hparams[HP_TOKEN_TYPE.name] == 'character':
        return character_tokenize

    return None


def build_lookup_table(keys, values=None, default_value=-1):

    if values is None:
        values = tf.range(len(keys))

    kv_init = tf.lookup.KeyValueTensorInitializer(
        keys=keys, values=values)

    return tf.lookup.StaticHashTable(kv_init,
        default_value=default_value)


def preprocess_input(inputs, 
                     tokenizer_fn,
                     vocab_table,
                     candidates_table):

    num_memories = tf.shape(inputs['memories'])[0]
    memories = tf.strings.split(inputs['memories'], 
        sep=' ', maxsplit=2).to_tensor()

    if tf.shape(memories)[1] > 1:
        mem_tok = tf.concat([memories[:, :2],
                             tokenizer_fn(memories[:, 2])], axis=1)
    else:
        padding = tf.fill([num_memories, 2], '')
        mem_tok = tf.concat([padding,
                             tokenizer_fn(inputs['memories'])], axis=1)

    mem_tok = mem_tok.to_tensor()
    mem_enc = vocab_table.lookup(mem_tok)

    inp_tok = tokenizer_fn(inputs['inputs'])
    inp_enc = vocab_table.lookup(inp_tok)

    out_enc = [candidates_table.lookup(inputs['outputs'])]

    return ({
        'memories': mem_enc,
        'inputs': inp_enc
    }, out_enc)


def preprocess_dataset(dataset,
                       tokenizer_fn,
                       vocab_table, 
                       candidates_table,
                       hparams):

    dataset = dataset.shuffle(5000)

    dataset = dataset.map(lambda inputs: (
        preprocess_input(inputs, 
            tokenizer_fn=tokenizer_fn,
            vocab_table=vocab_table,
            candidates_table=candidates_table)),
        num_parallel_calls=tf.data.experimental.AUTOTUNE)

    dataset = dataset.padded_batch(hparams[HP_BATCH_SIZE.name], 
        padded_shapes=({
            'memories': [-1, -1],
            'inputs': [-1]
        }, [-1]))

    dataset = dataset.prefetch(tf.data.experimental.AUTOTUNE)
    dataset = dataset.repeat()

    return dataset