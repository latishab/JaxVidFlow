import functools
import math

import jax
from jax import numpy as jnp

def _nearest_multiple_of(x: float, multiple_of: int) -> int:
  return int(round(x / multiple_of)) * multiple_of

@functools.partial(jax.jit, static_argnames=['new_width', 'new_height', 'multiple_of', 'filter_method'])
def scale_image(img: jnp.ndarray, new_width: int | None = None, new_height: int | None = None,
                multiple_of: int = 2, filter_method: str = 'lanczos3') -> jnp.ndarray:
  if new_width is None and new_height is None:
    raise ValueError('Either new_width or new_height must be set')
  old_height, old_width = img.shape[:2]
  if new_width is None:
    new_width = _nearest_multiple_of(new_height / old_height * old_width, multiple_of)
  if new_height is None:
    new_height = _nearest_multiple_of(new_width / old_width * old_height, multiple_of)
  # First, if we are downsampling in either dim, by a factor of 2 or more, we use reduce_window()
  # to downsample by integer window first. This both handles the common case of integer downsamples
  # very fast, and also prevents aliasing when doing a large ratio downsample using a filter, where
  # each output pixel only depends on non-contiguous sets of input pixels.
  # See https://en.wikipedia.org/wiki/Mipmap
  height_ds_factor = max(int(math.floor(old_height / new_height)), 1)
  width_ds_factor = max(int(math.floor(old_width / new_width)), 1)
  if height_ds_factor >= 2 or width_ds_factor >= 2:
    window = (height_ds_factor, width_ds_factor, 1)
    img = jax.lax.reduce_window(img,
      init_value=0.0, computation=jax.lax.add,
      window_dimensions=window,
      window_strides=window, padding='valid') / height_ds_factor / width_ds_factor
  # Now we do the filter-based stuff if necessary.
  if img.shape[:2] != (new_height, new_width):
    img = jax.image.resize(img, (new_height, new_width, img.shape[2]), method=filter_method)
  assert img.shape[:2] == (new_height, new_width)
  return img