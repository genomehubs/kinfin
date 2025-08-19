import React, { useState, useEffect } from "react";
import styles from "./Home.module.scss";
import { Button, Dialog, DialogContent, IconButton, Box } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useNavigate } from "react-router-dom";
import { CAROUSEL_IMAGES, HOME_PAGE_CONFIG } from "../../utilis/constants";
import Navbar from "../../components/Navbar";

const Home = () => {
  const navigate = useNavigate();

  const [isVideoOpen, setIsVideoOpen] = useState(false);
  const [currentImage, setCurrentImage] = useState(0);
  const [fade, setFade] = useState(false);

  useEffect(() => {
    const interval = setInterval(() => {
      setFade(true);
      setTimeout(() => {
        setCurrentImage((prev) => (prev + 1) % CAROUSEL_IMAGES.length);
        setFade(false);
      }, 500);
    }, HOME_PAGE_CONFIG.carouselInterval);
    return () => clearInterval(interval);
  }, []);

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Navbar variant="landing" />

      <div className={styles.homeContainer}>
        <div className={styles.contentWrapper}>
          <div className={styles.leftSection}>
            <h1>{HOME_PAGE_CONFIG.title}</h1>
            <p>{HOME_PAGE_CONFIG.description}</p>

            <div className={styles.buttonGroup}>
              <Button
                variant="outlined"
                color="primary"
                onClick={() => setIsVideoOpen(true)}
                sx={{ padding: "10px 20px" }}
              >
                View Demo
              </Button>
              <Button
                variant="contained"
                color="primary"
                onClick={() => {
                  navigate("/define-node-labels");
                }}
                sx={{ padding: "10px 20px" }}
              >
                Start Analysis
              </Button>
            </div>
          </div>

          <div className={styles.rightSection}>
            <div className={styles.carouselWrapper}>
              <img
                src={CAROUSEL_IMAGES[currentImage].src}
                alt={CAROUSEL_IMAGES[currentImage].caption}
                title={CAROUSEL_IMAGES[currentImage].tooltip}
                className={`${styles.carouselImage} ${
                  fade ? styles.fadeOut : ""
                }`}
                onError={(e) => {
                  e.target.onerror = null;
                  e.target.src = "/images/fallback.png";
                }}
              />
              {CAROUSEL_IMAGES[currentImage].caption && (
                <p className={styles.caption}>
                  {CAROUSEL_IMAGES[currentImage].caption}
                </p>
              )}
            </div>
          </div>
        </div>

        <Dialog
          open={isVideoOpen}
          onClose={() => setIsVideoOpen(false)}
          maxWidth="md"
          fullWidth
        >
          <DialogContent sx={{ position: "relative", padding: 0 }}>
            <IconButton
              onClick={() => setIsVideoOpen(false)}
              sx={{
                position: "absolute",
                right: 8,
                top: 8,
                zIndex: 1,
                color: "#fff",
                backgroundColor: "rgba(0,0,0,0.5)",
                "&:hover": { backgroundColor: "rgba(0,0,0,0.7)" },
              }}
            >
              <CloseIcon />
            </IconButton>

            <div className={styles.videoWrapper}>
              <iframe
                src={HOME_PAGE_CONFIG.demoVideoUrl}
                title="KinFin Demo Video"
                frameBorder="0"
                allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                allowFullScreen
              />
            </div>
          </DialogContent>
        </Dialog>
      </div>
    </Box>
  );
};

export default Home;
