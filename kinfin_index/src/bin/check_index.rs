use anyhow::Result;
use clap::Parser;
use std::path::PathBuf;
use kinfin_index::memmap::MemmapIndex;

#[derive(Parser, Debug)]
struct Args {
    /// Path to memmap index file
    #[arg(short, long)]
    index: PathBuf,
}

fn main() -> Result<()> {
    let args = Args::parse();
    let mi = MemmapIndex::open(&args.index)?;
    let seq_len = mi.seq_len_raw_slice()?;
    let total = seq_len.len();
    let present = seq_len.iter().filter(|&&v| v != u32::MAX).count();
    println!("seq_count: {}  seq_len_present: {}  missing: {}", total, present, total - present);
    let show = std::cmp::min(20, total);
    if show > 0 {
        let sample: Vec<u32> = seq_len[..show].iter().copied().collect();
        println!("first {} seq_len values: {:?}", show, sample);
    }
    Ok(())
}
